"""Opt-in integration of the executable contract with durable orchestration."""
import asyncio
from pathlib import Path
import os
import tempfile
import unittest
from uuid import uuid4

from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from examples.purchase import interfaces
from examples.purchase.contract import SPEC
from examples.purchase.handlers import registry
from examples.purchase.services import Services
from examples.purchase.temporal_workflow import ApprovePurchase, ConfirmPurchase
from myworkflow.executable import Engine, Program
from myworkflow.temporal import PipelineActivity


class PurchaseTemporalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        executable = os.environ.get('TEMPORAL_CLI_PATH')
        if not executable:
            raise RuntimeError('Set TEMPORAL_CLI_PATH')
        self.environment = await WorkflowEnvironment.start_local(dev_server_existing_path=executable)
        self.addAsyncCleanup(self.environment.shutdown)
        self.services = Services(Path(self.tmp.name) / 'purchase.db')
        self.activity = PipelineActivity(Engine(Program(SPEC), registry, self.services, interfaces))
        self.queue = f'purchase-{uuid4()}'

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
            self.assertEqual(self.services.application('x')['status'], 'waiting-approval')
        # The worker disappears while waiting. A new worker replays persisted history.
        async with self.worker():
            await handle.signal(ApprovePurchase.decide, {'approved': True, 'actor': 'bob', 'roles': ['role.approver']})
            await handle.signal(ApprovePurchase.decide, {'approved': False, 'actor': 'bob', 'roles': ['role.approver']})
            result = await asyncio.wait_for(handle.result(), 20)
        self.assertEqual(result['status'], 'confirmed')
        self.assertEqual(self.services.application('x')['status'], 'confirmed')
        with self.services.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM orders').fetchone()[0], 1)
        history = await handle.fetch_history()
        self.assertTrue(any(e.HasField('timer_started_event_attributes') for e in history.events))
        child = next(e.start_child_workflow_execution_initiated_event_attributes for e in history.events
                     if e.HasField('start_child_workflow_execution_initiated_event_attributes'))
        self.assertEqual(child.workflow_type.name, SPEC['workflows'][0]['bindings'][2]['next_workflow'])

    async def test_rejection_never_starts_confirmation(self):
        async with self.worker():
            handle = await self.start()
            await handle.signal(ApprovePurchase.decide, {'approved': False, 'actor': 'bob', 'roles': ['role.approver']})
            self.assertEqual((await asyncio.wait_for(handle.result(), 20))['status'], 'rejected')
        history = await handle.fetch_history()
        self.assertFalse(any(e.HasField('start_child_workflow_execution_initiated_event_attributes') for e in history.events))
        with self.services.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM orders').fetchone()[0], 0)

    async def test_unauthorized_approval_fails_without_order(self):
        async with self.worker():
            handle = await self.start()
            await handle.signal(ApprovePurchase.decide, {'approved': True, 'actor': 'mallory', 'roles': ['role.requester']})
            with self.assertRaises(WorkflowFailureError) as caught:
                await asyncio.wait_for(handle.result(), 20)
            application_error = caught.exception.cause.cause
            self.assertEqual(application_error.type, 'PermissionDenied')
            self.assertIn('secondary_errors', application_error.details[0])
        self.assertEqual(self.services.application('x')['status'], 'waiting-approval')
