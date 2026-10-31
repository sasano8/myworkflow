"""Explicit opt-in: python -m unittest discover -s integration -v."""
import asyncio
import os
import unittest
from uuid import uuid4

from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from examples.approval import catalog
from examples.temporal_purchase import ApprovePurchase, ConfirmPurchase, confirm_order


class TemporalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        executable = os.environ.get("TEMPORAL_CLI_PATH")
        if not executable:
            raise RuntimeError("Set TEMPORAL_CLI_PATH to a verified Temporal CLI executable")
        self.environment = await WorkflowEnvironment.start_local(dev_server_existing_path=executable)
        self.addAsyncCleanup(self.environment.shutdown)

    async def test_approval_wait_timer_and_child_workflow(self):
        queue = f"purchase-{uuid4()}"
        async with Worker(self.environment.client, task_queue=queue,
                          workflows=[ApprovePurchase, ConfirmPurchase], activities=[confirm_order]):
            handle = await self.environment.client.start_workflow(
                ApprovePurchase.run,
                {"application_id": "purchase-001", "quote_registered": True, "delay_seconds": 0.2},
                id=str(uuid4()), task_queue=queue,
            )
            self.assertEqual(await handle.query(ApprovePurchase.state), "waiting-approval")
            history = await handle.fetch_history()
            self.assertFalse(any(e.HasField("start_child_workflow_execution_initiated_event_attributes") for e in history.events))
            await handle.signal(ApprovePurchase.approve)
            self.assertEqual(await asyncio.wait_for(handle.result(), 20),
                             {"application_id": "purchase-001", "status": "confirmed-demo"})
            history = await handle.fetch_history()
            self.assertTrue(any(e.HasField("timer_started_event_attributes") for e in history.events))
            child = next(e.start_child_workflow_execution_initiated_event_attributes for e in history.events
                         if e.HasField("start_child_workflow_execution_initiated_event_attributes"))
            self.assertEqual(child.workflow_type.name, catalog.workflows[2].id)

    async def test_missing_quotation_fails(self):
        queue = f"purchase-{uuid4()}"
        async with Worker(self.environment.client, task_queue=queue,
                          workflows=[ConfirmPurchase], activities=[confirm_order]):
            with self.assertRaises(WorkflowFailureError):
                await asyncio.wait_for(self.environment.client.execute_workflow(
                    ConfirmPurchase.run, {"application_id": "purchase-002", "approved": True, "quote_registered": False},
                    id=str(uuid4()), task_queue=queue,
                ), 20)
