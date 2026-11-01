"""Opt-in integration of the executable contract with durable orchestration."""
import asyncio
import os
from uuid import uuid4

import pytest
import pytest_asyncio

from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from examples.purchase import interfaces
from examples.purchase.contract import program
from examples.purchase.handlers import registry
from examples.purchase.services import Services
from examples.purchase.temporal_workflow import ApprovePurchase, ConfirmPurchase
from myworkflow.executable import Engine, Principal, Program
from myworkflow.temporal import PipelineActivity


@pytest.mark.asyncio(loop_scope="function")
class TestPurchaseTemporal:
    @pytest_asyncio.fixture(autouse=True, loop_scope="function")
    async def prepare(self, tmp_path):
        executable = os.environ.get('TEMPORAL_CLI_PATH')
        if not executable:
            raise RuntimeError('Set TEMPORAL_CLI_PATH')
        self.environment = await WorkflowEnvironment.start_local(dev_server_existing_path=executable)
        try:
            self.services = Services(tmp_path / 'purchase.db')
            self.activity = PipelineActivity(Engine(program, registry, self.services, interfaces))
            self.queue = f'purchase-{uuid4()}'
            yield
        finally:
            await self.environment.shutdown()

    def worker(self):
        return Worker(self.environment.client, task_queue=self.queue,
                      workflows=[ApprovePurchase, ConfirmPurchase], activities=[self.activity.invoke])

    async def start(self):
        handle = await self.environment.client.start_workflow(
            ApprovePurchase.run, {'application_id': 'x', 'vendor': 'V', 'amount': 100,
                                 'quote_a': 'A', 'quote_b': 'B', 'applicant': 'alice', 'delay_seconds': 0.1},
            id=str(uuid4()), task_queue=self.queue)
        async with asyncio.timeout(20):
            while await handle.query(ApprovePurchase.state) != 'waiting-approval':
                await asyncio.sleep(0.02)
        return handle

    async def test_worker_restart_duplicate_signal_timer_and_real_order(self):
        async with self.worker():
            handle = await self.start()
            assert self.services.application('x')['status'] == 'waiting-approval'
            history = await handle.fetch_history()
            assert not any((e.HasField('start_child_workflow_execution_initiated_event_attributes') for e in history.events))
            with self.services.connect() as db:
                assert db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
        # The worker disappears while waiting. A new worker replays persisted history.
        async with self.worker():
            await handle.signal(ApprovePurchase.decide, {'approved': True, 'actor': 'bob', 'roles': ['role.approver']})
            await handle.signal(ApprovePurchase.decide, {'approved': False, 'actor': 'bob', 'roles': ['role.approver']})
            result = await asyncio.wait_for(handle.result(), 20)
        assert result['status'] == 'confirmed'
        assert self.services.application('x')['status'] == 'confirmed'
        with self.services.connect() as db:
            assert db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        history = await handle.fetch_history()
        assert any((e.HasField('timer_started_event_attributes') for e in history.events))
        child = next(e.start_child_workflow_execution_initiated_event_attributes for e in history.events
                     if e.HasField('start_child_workflow_execution_initiated_event_attributes'))
        assert child.workflow_type.name == self.activity.engine.program.binding('b.dispatch').next_workflow_id

    async def test_rejection_never_starts_confirmation(self):
        async with self.worker():
            handle = await self.start()
            await handle.signal(ApprovePurchase.decide, {'approved': False, 'actor': 'bob', 'roles': ['role.approver']})
            assert (await asyncio.wait_for(handle.result(), 20))['status'] == 'rejected'
        history = await handle.fetch_history()
        assert not any((e.HasField('start_child_workflow_execution_initiated_event_attributes') for e in history.events))
        with self.services.connect() as db:
            assert db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0

    async def test_unauthorized_approval_fails_without_order(self):
        async with self.worker():
            handle = await self.start()
            await handle.signal(ApprovePurchase.decide, {'approved': True, 'actor': 'mallory', 'roles': ['role.requester']})
            with pytest.raises(WorkflowFailureError) as caught:
                await asyncio.wait_for(handle.result(), 20)
            application_error = caught.value.cause.cause
            assert application_error.type == 'PermissionDenied'
            assert 'secondary_errors' in application_error.details[0]
        assert self.services.application('x')['status'] == 'waiting-approval'

    async def test_missing_quotation_fails_without_order(self):
        engine = self.activity.engine
        engine.invoke('b.submit', 't.submit', {'id': 'x', 'vendor': 'V', 'amount': 100},
                      Principal('alice', frozenset({'role.requester'})), run_id='submit')
        engine.invoke('b.approve', 't.approve', {'id': 'x', 'decision': True},
                      Principal('bob', frozenset({'role.approver'})), run_id='approve')
        async with self.worker():
            with pytest.raises(WorkflowFailureError):
                await asyncio.wait_for(self.environment.client.execute_workflow(
                    ConfirmPurchase.run, {'application_id': 'x'}, id=str(uuid4()), task_queue=self.queue), 20)
        assert self.services.application('x')['status'] == 'approved'
        with self.services.connect() as db:
            assert db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
