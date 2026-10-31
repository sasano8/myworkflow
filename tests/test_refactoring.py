"""Behavioral checks for immutable contracts and infrastructure boundaries."""
from contextlib import contextmanager
import copy
from dataclasses import FrozenInstanceError
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from examples.tickets.contract import SPEC
from examples.tickets.application import engine as ticket_engine
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


class RefactoringTests(unittest.TestCase):
    def test_contract_is_immutable_and_uses_one_model(self):
        source = copy.deepcopy(SPEC)
        program = Program(source)
        source['pipelines'][0]['name'] = 'changed'
        snapshot = program.spec
        snapshot['pipelines'][0]['name'] = 'also changed'
        self.assertEqual(program.plans['ticket.issue'].name, 'チケット発行')
        self.assertIs(program.catalog().pipelines[0], program.plans['ticket.issue'])
        with self.assertRaises(FrozenInstanceError):
            program.plans['ticket.issue'].name = 'bad'
        with self.assertRaises(TypeError):
            program.plans['other'] = None

    def test_malformed_contracts_have_domain_errors(self):
        cases = [{}, {'artifacts': None}, copy.deepcopy(SPEC), copy.deepcopy(SPEC)]
        cases[2]['pipelines'][0]['steps'][1]['when'] = [[], True]
        cases[3]['workflows'][0]['bindings'][0]['triggers'][0]['mapping'] = None
        for spec in cases:
            with self.subTest(spec=spec), self.assertRaises(ContractError):
                Program(spec)

    def test_tested_condition_cannot_be_reassigned(self):
        spec = copy.deepcopy(SPEC)
        spec['artifacts'].append({'id': 'ticket.flag', 'name': '判定', 'key': 'flag', 'type': 'bool'})
        steps = spec['pipelines'][0]['steps']
        steps.insert(1, {'id': 'ticket.flag-init', 'name': '判定', 'summary': '判定', 'kind': 'action', 'reads': [], 'writes': ['ticket.flag']})
        steps[2]['when'] = ['ticket.flag', True]
        steps.append({'id': 'ticket.flag-change', 'name': '変更', 'summary': '変更', 'kind': 'action', 'reads': [], 'writes': ['ticket.flag']})
        with self.assertRaisesRegex(ContractError, 'reassigned'):
            Program(spec)

    def test_registry_replacement_is_explicit_and_validated(self):
        registry = Registry()
        @registry.implements('ticket.save')
        def original(ctx: Context) -> None: pass
        fork = registry.fork()
        @fork.implements('ticket.other')
        def replacement(ctx: Context) -> None: pass
        fork.replace('ticket.save', replacement)
        self.assertIs(registry.handlers['ticket.save'], original)
        with self.assertRaises(TypeError): registry.handlers['ticket.save'] = replacement
        with self.assertRaises(ContractError): fork.replace('ticket.save', lambda ctx: None)

    def test_engine_works_without_database_or_purchase_services(self):
        program = Program(SPEC)
        registry = Registry()
        @registry.implements('ticket.save')
        def issue(ctx: Context) -> None: ctx.values['receipt'] = 'done'
        journal = MemoryJournal()
        runner = Engine(program, registry, object(), locks=InProcessLockProvider(), store=journal)
        result = runner.invoke('ticket.binding', 'ticket.trigger', {'受付番号': 'a'}, Principal('operator', frozenset({'ticket.operator'})), run_id='one')
        self.assertEqual(result, {'receipt': 'done'})
        self.assertEqual(journal.runs['one'][0], 'completed')

    def test_original_error_survives_cleanup_and_journal_failures(self):
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
        with self.assertRaises(ExecutionFailed) as caught:
            runner.run_internal('ticket.issue', {'number': 'x'}, actor='op', run_id='x')
        self.assertEqual(caught.exception.step_id, 'ticket.save')
        self.assertEqual(str(caught.exception.cause), 'business failure')
        self.assertEqual({e[0] for e in caught.exception.secondary_errors}, {'lock-release', 'journal'})

    def test_empty_pipeline_journal_error_has_pipeline_location(self):
        spec = copy.deepcopy(SPEC)
        spec['pipelines'][0].update(steps=[], inputs=[], outputs=[])
        spec['workflows'][0]['bindings'][0]['triggers'][0]['mapping'] = {}
        class BrokenJournal(MemoryJournal):
            def record(self, *args): raise OSError('journal unavailable')
        runner = Engine(Program(spec), Registry(), object(), store=BrokenJournal())
        with self.assertRaises(ExecutionFailed) as caught:
            runner.run_internal('ticket.issue', {}, actor='op', run_id='x')
        self.assertEqual(caught.exception.step_id, 'ticket.issue/journal')

    def test_shared_provider_and_typed_order_independent_keys(self):
        provider = InProcessLockProvider()
        key = (('second', 2), ('first', 'x'))
        self.assertEqual(canonical_key(key), canonical_key(tuple(reversed(key))))
        self.assertNotEqual(canonical_key((('a', True),)), canonical_key((('a', 1),)))
        with provider.acquire(key):
            with self.assertRaises(LockConflict):
                with provider.acquire(tuple(reversed(key)), timeout=0.001): pass
            with provider.acquire(key, namespace='other'): pass
        with provider.acquire(key): pass
        self.assertEqual(provider._entries, {})

    def test_two_applications_share_locks_but_not_execution_ids(self):
        from examples.purchase.services import Services
        from examples.purchase.contract import SPEC as PURCHASE_SPEC
        from examples.purchase.handlers import registry
        with tempfile.TemporaryDirectory() as directory:
            locks = InProcessLockProvider()
            services = Services(Path(directory) / 'purchase.db', locks=locks)
            other = Services(services.database, locks=locks)
            with services.lock((('a.id', 'a'),)):
                with self.assertRaises(LockConflict):
                    with other.lock((('a.id', 'a'),)): pass
            self.assertNotEqual(execution_id('a/b', 'c'), execution_id('a_b', 'c'))
            runner = Engine(Program(PURCHASE_SPEC), registry, services)
            for application in ('a', 'b'):
                runner.invoke('b.submit', 't.submit', {'id': application, 'vendor': 'V', 'amount': 1},
                              Principal('op', frozenset({'role.requester'})), run_id=execution_id(application, 'submit'))
            with services.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM applications').fetchone()[0], 2)

    def test_generation_rolls_back_all_outputs_if_replace_fails(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory) / 'a', Path(directory) / 'b'
            a.write_text('old-a'); b.write_text('old-b')
            replace = os.replace
            def fail_second(src, dst):
                if dst == b: raise OSError('disk error')
                return replace(src, dst)
            with patch('myworkflow.generation.os.replace', side_effect=fail_second):
                with self.assertRaises(OSError): write_outputs({a: 'new-a', b: 'new-b'})
            self.assertEqual(a.read_text(), 'old-a')
            self.assertEqual(b.read_text(), 'old-b')
            self.assertEqual(set(Path(directory).iterdir()), {a, b})

    def test_compensation_uses_step_boundary_values_not_later_mutations(self):
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
        with self.assertRaises(ExecutionFailed):
            runner.run_internal('ticket.issue', {'number': 'n'}, actor='op', run_id='n')
        self.assertEqual(observed, ['created'])

    def test_response_constructor_failure_is_attributed_before_completion(self):
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
        runner = Engine(program, registry, object(), interfaces, locks=InProcessLockProvider(), store=journal)
        with self.assertRaises(ExecutionFailed) as caught:
            runner.run_internal('ticket.issue', {'number': 'n'}, actor='op', run_id='n')
        self.assertEqual(caught.exception.step_id, 'ticket.issue/response')
        self.assertEqual(journal.runs['n'][0], 'failed')

    def test_two_scheduled_purchases_share_services_without_colliding(self):
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
                runner.invoke('b.submit', 't.submit', {'id': identity, 'vendor': 'V', 'amount': 1}, applicant, run_id=execution_id(identity, 'submit'))
                runner.invoke('b.upload', 't.upload', {'id': identity, 'file_a': 'A', 'file_b': 'B'}, applicant, run_id=execution_id(identity, 'upload'))
                flow = ScheduledPurchase(runner, clock, clock.now(), application_id=identity, run_id=identity)
                flow.approve(True, approver)
                flow.tick()
                self.assertTrue(flow.completed)
            with services.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM orders').fetchone()[0], 2)
