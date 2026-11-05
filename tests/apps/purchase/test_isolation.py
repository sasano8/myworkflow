"""purchase behavior and invariants."""

from pathlib import Path
import tempfile
import pytest
from myworkflow.executable import Engine, Principal
from myworkflow.contracts.identity import execution_id
from myworkflow.adapters.inprocess import InProcessLockProvider, LockConflict


def test_two_applications_share_locks_but_not_execution_ids():
    from examples.apps.purchase.services import Services
    from examples.apps.purchase.contract import program as purchase_program
    from examples.apps.purchase.handlers import registry

    with tempfile.TemporaryDirectory() as directory:
        locks = InProcessLockProvider()
        services = Services(Path(directory) / "purchase.db", locks=locks)
        other = Services(services.database, locks=locks)
        with services.lock((("a.id", "a"),)):
            with pytest.raises(LockConflict):
                with other.lock((("a.id", "a"),)):
                    pass
        assert execution_id("a/b", "c") != execution_id("a_b", "c")
        runner = Engine(purchase_program, registry, services)
        for application in ("a", "b"):
            runner.invoke_or_raise(
                "b.submit",
                "t.submit",
                {"id": application, "vendor": "V", "amount": 1},
                Principal("op", frozenset({"role.requester"})),
                run_id=execution_id(application, "submit"),
            )
        with services.connect() as db:
            assert db.execute("SELECT count(*) FROM applications").fetchone()[0] == 2


def test_two_scheduled_purchases_share_services_without_colliding():
    from datetime import datetime
    from types import SimpleNamespace
    from examples.apps.purchase.services import Services
    from examples.apps.purchase.contract import program as purchase_program
    from examples.apps.purchase.handlers import registry
    from examples.apps.purchase.scheduling import ScheduledPurchase

    with tempfile.TemporaryDirectory() as directory:
        services = Services(Path(directory) / "purchase.db")
        runner = Engine(purchase_program, registry, services)
        applicant = Principal("applicant", frozenset({"role.requester"}))
        approver = Principal("approver", frozenset({"role.approver"}))
        clock = SimpleNamespace(
            now=lambda: datetime.fromisoformat("2030-04-01T10:00:00+09:00")
        )
        for identity in ("first", "second"):
            runner.invoke_or_raise(
                "b.submit",
                "t.submit",
                {"id": identity, "vendor": "V", "amount": 1},
                applicant,
                run_id=execution_id(identity, "submit"),
            )
            runner.invoke_or_raise(
                "b.upload",
                "t.upload",
                {"id": identity, "file_a": "A", "file_b": "B"},
                applicant,
                run_id=execution_id(identity, "upload"),
            )
            flow = ScheduledPurchase(
                runner, clock, clock.now(), application_id=identity, run_id=identity
            )
            flow.approve(True, approver)
            flow.tick()
            assert flow.completed
        with services.connect() as db:
            assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 2
