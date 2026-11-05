"""Scenario state and adapters for the purchase application."""

import asyncio
from pathlib import Path

from examples.apps.purchase import contract as c
from examples.apps.purchase.handlers import registry
from examples.apps.purchase.scheduling import ScheduledPurchase, aware_time
from examples.apps.purchase.services import Services
from myworkflow.executable import Engine, Principal, Program, Registry
from myworkflow.contracts.results import PipelineResult


class ManualClock:
    def __init__(self):
        self.instant = aware_time("2030-04-01T09:00:00+09:00")

    def now(self):
        return self.instant

    def advance(self, instant):
        instant = aware_time(instant)
        if instant < self.instant:
            raise ValueError("Clock cannot move backwards")
        self.instant = instant


class World:
    def __init__(self, directory):
        from examples.apps.purchase import interfaces

        self.services = Services(Path(directory) / "purchase.sqlite")
        self.program = c.program
        self.registry = registry.fork()
        self.engine = Engine(self.program, self.registry, self.services, interfaces)
        self.application_id = "purchase-001"
        self.run_id = "purchase-acceptance"
        self.clock = ManualClock()
        self.flow = ScheduledPurchase(
            self.engine,
            self.clock,
            "2030-04-01T10:00:00+09:00",
            application_id=self.application_id,
            run_id=self.run_id,
        )
        self.applicant = Principal("alice", frozenset({c.requester.id}))
        self.approver = Principal("bob", frozenset({c.approver.id}))
        self.system = Principal("scheduler", frozenset({c.system.id}))
        self.sequence = 0
        self.error = None
        self.result = None
        self.driver = None
        self.mutation = None

    def invoke(self, binding, trigger, payload, principal, run_id=None):
        self.sequence += 1
        return self.engine.invoke(
            binding,
            trigger,
            payload,
            principal,
            run_id=run_id or f"acceptance-{self.sequence}",
        )

    def attempt(self, action):
        self.error = None
        self.result = None
        try:
            self.result = action()
            if isinstance(self.result, PipelineResult) and not self.result.ok:
                self.error = self.result
        except Exception as exc:
            self.error = exc

    def prepare(self, quotes):
        self.invoke(
            c.PurchaseApproval.submit,
            c.PurchaseApproval.submission,
            {"id": "purchase-001", "vendor": "サンプル商事", "amount": 10000},
            self.applicant,
        )
        if quotes:
            self.upload()

    def upload(self):
        return self.invoke(
            c.PurchaseAttachment.upload,
            c.PurchaseAttachment.attachment_received,
            {"id": "purchase-001", "file_a": "見積書A", "file_b": "見積書B"},
            self.applicant,
            "upload",
        )

    def decide(self, decision, principal=None):
        if self.driver:
            self.driver.decide(decision)
            return
        if self.mutation == "early":
            self.flow.due_at = self.clock.now()
        if self.mutation == "rejected-order" and not decision:
            decision = True
        duplicate = self.flow.decision is not None
        self.flow.approve(decision, principal or self.approver)
        if self.mutation == "duplicate" and duplicate:
            with self.services.connect() as db:
                db.execute(
                    "INSERT INTO orders VALUES (?,?)", ("extra-order", "purchase-001")
                )

    def advance(self, instant):
        self.clock.advance(instant)
        self.flow.tick()

    def count(self, table):
        if table not in {"orders", "objects", "attachments"}:
            raise ValueError("Unsupported assertion table")
        with self.services.connect() as db:
            return db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    def run_status(self):
        with self.services.connect() as db:
            row = db.execute(
                "SELECT status FROM runs WHERE id=?", ("upload",)
            ).fetchone()
        return row[0] if row else None

    def status(self):
        with self.services.connect() as db:
            row = db.execute(
                "SELECT status FROM applications WHERE id=?", ("purchase-001",)
            ).fetchone()
        return row[0] if row else None

    def recover(self):
        self.services = Services(self.services.database)
        self.services.recover("upload")

    def diagnose(self):
        return {
            "application_status": self.status(),
            "orders": self.count("orders"),
            "objects": self.count("objects"),
            "attachments": self.count("attachments"),
            "last_error": type(self.error).__name__ if self.error else None,
            "upload_status": self.run_status(),
        }

    def close(self):
        if self.driver:
            self.driver.close()

    def start_temporal(self):
        if self.driver:
            raise ValueError("Temporal is already running")
        self.driver = TemporalDriver(self)


class TemporalDriver:
    """Keep SDK tasks on one loop. Every wait is bounded and state-based."""

    def __init__(self, world):
        self.world = world
        self.runner = asyncio.Runner()
        self.harness = None
        try:
            self.runner.run(self.start())
        except BaseException:
            self.close()
            raise

    async def start(self):
        import os
        from uuid import uuid4
        from myworkflow.adapters.temporal_testing import TemporalHarness
        from examples.apps.purchase.temporal_workflow import (
            ApprovePurchase,
            ConfirmPurchase,
        )
        from myworkflow.adapters.temporal import PipelineActivity

        executable = os.environ.get("TEMPORAL_CLI_PATH")
        if not executable:
            raise RuntimeError(
                "Set TEMPORAL_CLI_PATH to run Temporal acceptance scenarios"
            )
        activity = PipelineActivity(self.world.engine)
        queue = f"acceptance-{uuid4()}"
        self.harness = TemporalHarness(
            executable,
            queue,
            workflows=[ApprovePurchase, ConfirmPurchase],
            activities=[activity.invoke],
        )
        await self.harness.__aenter__()
        self.handle = await self.harness.client.start_workflow(
            ApprovePurchase.run,
            {
                "application_id": "purchase-001",
                "vendor": "サンプル商事",
                "amount": 10000,
                "quote_a": "見積書A",
                "quote_b": "見積書B",
                "applicant": "alice",
                "delay_seconds": 0.1,
            },
            id=f"acceptance-{uuid4()}",
            task_queue=queue,
        )
        async with asyncio.timeout(20):
            while await self.handle.query(ApprovePurchase.state) != "waiting-approval":
                await asyncio.sleep(0.02)

    def decide(self, decision):
        from examples.apps.purchase.temporal_workflow import ApprovePurchase

        async def send():
            async with asyncio.timeout(20):
                await self.handle.signal(
                    ApprovePurchase.decide,
                    {"approved": decision, "actor": "bob", "roles": [c.approver.id]},
                )

        self.runner.run(send())

    def finish(self):
        async def wait():
            async with asyncio.timeout(20):
                return await self.handle.result()

        return self.runner.run(wait())

    def close(self):
        async def stop():
            if self.harness:
                await self.harness.__aexit__(None, None, None)

        try:
            self.runner.run(stop())
        finally:
            self.runner.close()
