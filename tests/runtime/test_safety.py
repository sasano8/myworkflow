"""runtime behavior and invariants."""

from contextlib import contextmanager
import copy
import pytest
from examples.apps.tickets.contract import SPEC, compiled
from myworkflow.executable import (
    Context,
    ContractError,
    Engine,
    ExecutionFailed,
    Principal,
    Program,
    Registry,
)
from myworkflow.adapters.inprocess import InProcessLockProvider


class MemoryJournal:
    def __init__(self):
        self.runs = {}

    def begin(self, run_id):
        if run_id in self.runs:
            raise ValueError("Duplicate execution")
        self.runs[run_id] = ("running", [])

    def record(self, run_id, events, status):
        self.runs[run_id] = (str(status), list(events))


def test_registry_replacement_is_explicit_and_validated():
    registry = Registry()

    @registry.implements("ticket.save")
    def original(ctx: Context) -> None:
        pass

    fork = registry.fork()

    @fork.implements("ticket.other")
    def replacement(ctx: Context) -> None:
        pass

    fork.replace("ticket.save", replacement)
    assert registry.handlers["ticket.save"] is original
    with pytest.raises(TypeError):
        registry.handlers["ticket.save"] = replacement
    with pytest.raises(ContractError):
        fork.replace("ticket.save", lambda ctx: None)


def test_engine_works_without_database_or_purchase_services():
    program = Program(SPEC, value_objects=compiled.catalog.value_objects)
    registry = Registry()

    @registry.implements("ticket.save")
    def issue(ctx: Context) -> None:
        ctx.values["receipt"] = "done"

    journal = MemoryJournal()
    runner = Engine(
        program, registry, object(), locks=InProcessLockProvider(), store=journal
    )
    result = runner.invoke_or_raise(
        "ticket.binding",
        "ticket.trigger",
        {"受付番号": "a"},
        Principal("operator", frozenset({"ticket.operator"})),
        run_id="one",
    )
    assert result.code == 0
    assert journal.runs["one"][0] == "completed"


def test_original_error_survives_cleanup_and_journal_failures():
    registry = Registry()

    @registry.implements("ticket.save")
    def fail(ctx: Context) -> None:
        raise ValueError("business failure")

    class BrokenJournal(MemoryJournal):
        def record(self, *args):
            raise OSError("journal unavailable")

    class BrokenLock:
        @contextmanager
        def acquire(self, key, **options):
            yield
            raise OSError("unlock unavailable")

    runner = Engine(
        Program(SPEC, value_objects=compiled.catalog.value_objects),
        registry,
        object(),
        locks=BrokenLock(),
        store=BrokenJournal(),
    )
    with pytest.raises(ExecutionFailed) as caught:
        runner.run_or_raise("ticket.issue", {"number": "x"}, actor="op", run_id="x")
    assert caught.value.step_id == "ticket.save"
    assert str(caught.value.cause) == "business failure"
    assert {e[0] for e in caught.value.secondary_errors} == {"lock-release", "journal"}


def test_empty_pipeline_journal_error_has_pipeline_location():
    spec = copy.deepcopy(SPEC)
    spec["pipelines"][0].update(steps=[], inputs=[], outputs=[])
    spec["workflows"][0]["bindings"][0]["triggers"][0]["mapping"] = {}

    class BrokenJournal(MemoryJournal):
        def record(self, *args):
            raise OSError("journal unavailable")

    runner = Engine(
        Program(spec, value_objects=compiled.catalog.value_objects),
        Registry(),
        object(),
        store=BrokenJournal(),
    )
    with pytest.raises(ExecutionFailed) as caught:
        runner.run_or_raise("ticket.issue", {}, actor="op", run_id="x")
    assert caught.value.step_id == "ticket.issue/journal"


def test_compensation_uses_step_boundary_values_not_later_mutations():
    spec = copy.deepcopy(SPEC)
    step = spec["pipelines"][0]["steps"][1]
    step["compensate"] = "ticket.undo"
    spec["pipelines"][0]["steps"].append(
        {
            "id": "ticket.fail",
            "name": "失敗",
            "summary": "失敗",
            "kind": "action",
            "reads": ["ticket.receipt"],
            "writes": ["ticket.receipt"],
        }
    )
    observed = []
    registry = Registry()

    @registry.implements("ticket.save")
    def create(ctx: Context) -> None:
        ctx.values["receipt"] = "created"

    @registry.implements("ticket.fail")
    def fail(ctx: Context) -> None:
        ctx.values["receipt"] = "later-value"
        raise ValueError("later failure")

    @registry.implements("ticket.undo")
    def undo(ctx: Context) -> None:
        observed.append(ctx.values["receipt"])

    runner = Engine(
        Program(spec, value_objects=compiled.catalog.value_objects),
        registry,
        object(),
        locks=InProcessLockProvider(),
        store=MemoryJournal(),
    )
    with pytest.raises(ExecutionFailed):
        runner.run_or_raise("ticket.issue", {"number": "n"}, actor="op", run_id="n")
    assert observed == ["created"]


def test_stale_business_response_is_rejected_before_execution():
    from dataclasses import make_dataclass
    from types import SimpleNamespace
    from myworkflow.generation.interfaces import interfaces_source

    program = Program(SPEC, value_objects=compiled.catalog.value_objects)
    interfaces = SimpleNamespace()
    exec(interfaces_source(program), interfaces.__dict__)

    def fail(instance):
        raise ValueError("bad response")

    interfaces.TicketIssueResponse = make_dataclass(
        "TicketIssueResponse", [("receipt", str)], namespace={"__post_init__": fail}
    )
    registry = Registry()

    @registry.implements("ticket.save")
    def issue(ctx: Context) -> None:
        ctx.values["receipt"] = "created"

    journal = MemoryJournal()
    with pytest.raises(ContractError, match="Response"):
        Engine(
            program,
            registry,
            object(),
            interfaces,
            locks=InProcessLockProvider(),
            store=journal,
        )
    assert journal.runs == {}
