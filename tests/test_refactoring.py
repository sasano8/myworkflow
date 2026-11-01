"""Behavioral checks for immutable contracts and infrastructure boundaries."""
from contextlib import contextmanager
import copy
from dataclasses import FrozenInstanceError
from pathlib import Path
import tempfile
import pytest

from examples.tickets.contract import SPEC
from myworkflow.executable import Context, ContractError, Engine, ExecutionFailed, Principal, Program, Registry
from myworkflow.generation import write_outputs
from myworkflow.identity import execution_id
from myworkflow.locking import InProcessLockProvider, LockConflict, canonical_key


class MemoryJournal:
    def __init__(self): self.runs = {}
    def begin(self, run_id):
        if run_id in self.runs: raise ValueError('Duplicate execution')
        self.runs[run_id] = ('running', [])
    def record(self, run_id, events, status): self.runs[run_id] = (str(status), list(events))


def test_contract_is_immutable_and_uses_one_model():
    source = copy.deepcopy(SPEC)
    program = Program(source)
    source['pipelines'][0]['name'] = 'changed'
    snapshot = program.spec
    snapshot['pipelines'][0]['name'] = 'also changed'
    assert program.plans['ticket.issue'].name == 'チケット発行'
    assert program.catalog().pipelines[0] is program.plans['ticket.issue']
    with pytest.raises(FrozenInstanceError):
        program.plans['ticket.issue'].name = 'bad'
    with pytest.raises(TypeError):
        program.plans['other'] = None


@pytest.mark.parametrize('case_index', range(4), ids=['empty', 'null-artifacts', 'invalid-condition', 'null-mapping'])
def test_malformed_contracts_have_domain_errors(case_index):
    cases = [{}, {'artifacts': None}, copy.deepcopy(SPEC), copy.deepcopy(SPEC)]
    cases[2]['pipelines'][0]['steps'][1]['when'] = [[], True]
    cases[3]['workflows'][0]['bindings'][0]['triggers'][0]['mapping'] = None
    spec = cases[case_index]
    with pytest.raises(ContractError):
        Program(spec)


def test_tested_condition_cannot_be_reassigned():
    spec = copy.deepcopy(SPEC)
    spec['artifacts'].append({'id': 'ticket.flag', 'name': '判定', 'key': 'flag', 'type': 'bool'})
    steps = spec['pipelines'][0]['steps']
    steps.insert(1, {'id': 'ticket.flag-init', 'name': '判定', 'summary': '判定', 'kind': 'action', 'reads': [], 'writes': ['ticket.flag']})
    steps[2]['when'] = ['ticket.flag', True]
    steps.append({'id': 'ticket.flag-change', 'name': '変更', 'summary': '変更', 'kind': 'action', 'reads': [], 'writes': ['ticket.flag']})
    with pytest.raises(ContractError, match='reassigned'):
        Program(spec)


def test_registry_replacement_is_explicit_and_validated():
    registry = Registry()
    @registry.implements('ticket.save')
    def original(ctx: Context) -> None: pass
    fork = registry.fork()
    @fork.implements('ticket.other')
    def replacement(ctx: Context) -> None: pass
    fork.replace('ticket.save', replacement)
    assert registry.handlers['ticket.save'] is original
    with pytest.raises(TypeError): registry.handlers['ticket.save'] = replacement
    with pytest.raises(ContractError): fork.replace('ticket.save', lambda ctx: None)


def test_engine_works_without_database_or_purchase_services():
    program = Program(SPEC)
    registry = Registry()
    @registry.implements('ticket.save')
    def issue(ctx: Context) -> None: ctx.values['receipt'] = 'done'
    journal = MemoryJournal()
    runner = Engine(program, registry, object(), locks=InProcessLockProvider(), store=journal)
    result = runner.invoke_or_raise('ticket.binding', 'ticket.trigger', {'受付番号': 'a'}, Principal('operator', frozenset({'ticket.operator'})), run_id='one')
    assert result.code == 0
    assert journal.runs['one'][0] == 'completed'


def test_original_error_survives_cleanup_and_journal_failures():
    registry = Registry()
    @registry.implements('ticket.save')
    def fail(ctx: Context) -> None: raise ValueError('business failure')
    class BrokenJournal(MemoryJournal):
        def record(self, *args): raise OSError('journal unavailable')
    class BrokenLock:
        @contextmanager
        def acquire(self, key, **options):
            yield
            raise OSError('unlock unavailable')
    runner = Engine(Program(SPEC), registry, object(), locks=BrokenLock(), store=BrokenJournal())
    with pytest.raises(ExecutionFailed) as caught:
        runner.run_or_raise('ticket.issue', {'number': 'x'}, actor='op', run_id='x')
    assert caught.value.step_id == 'ticket.save'
    assert str(caught.value.cause) == 'business failure'
    assert {e[0] for e in caught.value.secondary_errors} == {'lock-release', 'journal'}


def test_empty_pipeline_journal_error_has_pipeline_location():
    spec = copy.deepcopy(SPEC)
    spec['pipelines'][0].update(steps=[], inputs=[], outputs=[])
    spec['workflows'][0]['bindings'][0]['triggers'][0]['mapping'] = {}
    class BrokenJournal(MemoryJournal):
        def record(self, *args): raise OSError('journal unavailable')
    runner = Engine(Program(spec), Registry(), object(), store=BrokenJournal())
    with pytest.raises(ExecutionFailed) as caught:
        runner.run_or_raise('ticket.issue', {}, actor='op', run_id='x')
    assert caught.value.step_id == 'ticket.issue/journal'


def test_shared_provider_and_typed_order_independent_keys():
    provider = InProcessLockProvider()
    key = (('second', 2), ('first', 'x'))
    assert canonical_key(key) == canonical_key(tuple(reversed(key)))
    assert canonical_key((('a', True),)) != canonical_key((('a', 1),))
    with provider.acquire(key):
        with pytest.raises(LockConflict):
            with provider.acquire(tuple(reversed(key)), timeout=0.001): pass
        with provider.acquire(key, namespace='other'): pass
    with provider.acquire(key): pass
    assert provider._entries == {}


def test_two_applications_share_locks_but_not_execution_ids():
    from examples.purchase.services import Services
    from examples.purchase.contract import SPEC as PURCHASE_SPEC
    from examples.purchase.handlers import registry
    with tempfile.TemporaryDirectory() as directory:
        locks = InProcessLockProvider()
        services = Services(Path(directory) / 'purchase.db', locks=locks)
        other = Services(services.database, locks=locks)
        with services.lock((('a.id', 'a'),)):
            with pytest.raises(LockConflict):
                with other.lock((('a.id', 'a'),)): pass
        assert execution_id('a/b', 'c') != execution_id('a_b', 'c')
        runner = Engine(Program(PURCHASE_SPEC), registry, services)
        for application in ('a', 'b'):
            runner.invoke_or_raise('b.submit', 't.submit', {'id': application, 'vendor': 'V', 'amount': 1},
                          Principal('op', frozenset({'role.requester'})), run_id=execution_id(application, 'submit'))
        with services.connect() as db:
            assert db.execute('SELECT count(*) FROM applications').fetchone()[0] == 2


def test_generation_rolls_back_all_outputs_if_replace_fails(monkeypatch):
    import os
    with tempfile.TemporaryDirectory() as directory:
        a, b = Path(directory) / 'a', Path(directory) / 'b'
        a.write_text('old-a'); b.write_text('old-b')
        replace = os.replace
        def fail_second(src, dst):
            if dst == b: raise OSError('disk error')
            return replace(src, dst)
        with monkeypatch.context() as patcher:
            patcher.setattr('myworkflow.generation.os.replace', fail_second)
            with pytest.raises(OSError): write_outputs({a: 'new-a', b: 'new-b'})
        assert a.read_text() == 'old-a'
        assert b.read_text() == 'old-b'
        assert set(Path(directory).iterdir()) == {a, b}


def test_compensation_uses_step_boundary_values_not_later_mutations():
    spec = copy.deepcopy(SPEC)
    step = spec['pipelines'][0]['steps'][1]
    step['compensate'] = 'ticket.undo'
    spec['pipelines'][0]['steps'].append({'id': 'ticket.fail', 'name': '失敗', 'summary': '失敗', 'kind': 'action', 'reads': ['ticket.receipt'], 'writes': ['ticket.receipt']})
    observed = []
    registry = Registry()
    @registry.implements('ticket.save')
    def create(ctx: Context) -> None: ctx.values['receipt'] = 'created'
    @registry.implements('ticket.fail')
    def fail(ctx: Context) -> None:
        ctx.values['receipt'] = 'later-value'
        raise ValueError('later failure')
    @registry.implements('ticket.undo')
    def undo(ctx: Context) -> None: observed.append(ctx.values['receipt'])
    runner = Engine(Program(spec), registry, object(), locks=InProcessLockProvider(), store=MemoryJournal())
    with pytest.raises(ExecutionFailed):
        runner.run_or_raise('ticket.issue', {'number': 'n'}, actor='op', run_id='n')
    assert observed == ['created']


def test_stale_business_response_is_rejected_before_execution():
    from dataclasses import make_dataclass
    from types import SimpleNamespace
    from myworkflow.codegen import interfaces_source
    program = Program(SPEC)
    interfaces = SimpleNamespace()
    exec(interfaces_source(program), interfaces.__dict__)
    def fail(instance): raise ValueError('bad response')
    interfaces.TicketIssueResponse = make_dataclass('TicketIssueResponse', [('receipt', str)], namespace={'__post_init__': fail})
    registry = Registry()
    @registry.implements('ticket.save')
    def issue(ctx: Context) -> None: ctx.values['receipt'] = 'created'
    journal = MemoryJournal()
    with pytest.raises(ContractError, match='Response'):
        Engine(program, registry, object(), interfaces, locks=InProcessLockProvider(), store=journal)
    assert journal.runs == {}


def test_two_scheduled_purchases_share_services_without_colliding():
    from datetime import datetime
    from types import SimpleNamespace
    from examples.purchase.services import Services
    from examples.purchase.contract import SPEC as PURCHASE_SPEC
    from examples.purchase.handlers import registry
    from examples.purchase.scheduling import ScheduledPurchase
    with tempfile.TemporaryDirectory() as directory:
        services = Services(Path(directory) / 'purchase.db')
        runner = Engine(Program(PURCHASE_SPEC), registry, services)
        applicant = Principal('applicant', frozenset({'role.requester'}))
        approver = Principal('approver', frozenset({'role.approver'}))
        clock = SimpleNamespace(now=lambda: datetime.fromisoformat('2030-04-01T10:00:00+09:00'))
        for identity in ('first', 'second'):
            runner.invoke_or_raise('b.submit', 't.submit', {'id': identity, 'vendor': 'V', 'amount': 1}, applicant, run_id=execution_id(identity, 'submit'))
            runner.invoke_or_raise('b.upload', 't.upload', {'id': identity, 'file_a': 'A', 'file_b': 'B'}, applicant, run_id=execution_id(identity, 'upload'))
            flow = ScheduledPurchase(runner, clock, clock.now(), application_id=identity, run_id=identity)
            flow.approve(True, approver)
            flow.tick()
            assert flow.completed
        with services.connect() as db:
            assert db.execute('SELECT count(*) FROM orders').fetchone()[0] == 2
