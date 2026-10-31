import copy
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest

from examples.purchase import interfaces
from examples.purchase.contract import SPEC
from examples.purchase.handlers import registry
from examples.purchase.services import Services
from myworkflow.executable import (Context, ContractError, Engine, ExecutionFailed, Principal,
                                   Program, Registry, interfaces_source, skeleton_source)
from myworkflow.scaffold import initialize

ROOT = Path(__file__).resolve().parents[1]


class ExecutableTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.services = Services(Path(self.tmp.name) / 'db.sqlite')
        self.program = Program(copy.deepcopy(SPEC))
        self.engine = Engine(self.program, registry, self.services, interfaces)
        self.requester = Principal('alice', frozenset({'role.requester'}))
        self.approver = Principal('bob', frozenset({'role.approver'}))
        self.system = Principal('scheduler', frozenset({'role.system'}))
        self.sequence = 0

    def invoke(self, binding, trigger, payload, actor=None, run_id=None, engine=None):
        self.sequence += 1
        return (engine or self.engine).invoke(binding, trigger, payload, actor or self.requester,
                                            run_id=run_id or f'run-{self.sequence}')

    def submit(self):
        return self.invoke('b.submit', 't.submit', {'id': 'x', 'vendor': 'Vendor', 'amount': 100})

    def upload(self, run_id='upload'):
        return self.invoke('b.upload', 't.upload', {'id': 'x', 'file_a': 'A', 'file_b': 'B'}, run_id=run_id)

    def decide(self, approved=True):
        return self.invoke('b.approve', 't.approve', {'id': 'x', 'decision': approved}, self.approver)

    def rows(self, table):
        with self.services.connect() as db:
            return db.execute(f'SELECT * FROM {table}').fetchall()

    def test_end_to_end_typed_interfaces_and_persistence(self):
        self.assertIsInstance(self.submit(), interfaces.PSubmitResponse)
        self.assertIsInstance(self.upload(), interfaces.PUploadResponse)
        self.assertEqual(self.decide().status, 'approved')
        self.invoke('b.confirm', 't.confirm', {'id': 'x'}, self.system)
        self.assertEqual(Services(self.services.database).application('x')['status'], 'confirmed')
        self.assertEqual(len(self.rows('orders')), 1)
        self.assertEqual(len(self.rows('attachments')), 2)

    def test_rejection_branch_does_not_approve_or_order(self):
        self.submit()
        self.assertEqual(self.decide(False).status, 'rejected')
        self.assertEqual(self.rows('orders'), [])
        events = json.loads(self.rows('runs')[-1][2])
        self.assertIn(['s.approve', 'skipped'], events)
        self.assertIn(['s.reject', 'completed'], events)
        with self.assertRaises(ExecutionFailed):
            self.invoke('b.dispatch', 't.timer', {'id': 'x'}, self.system)

    def test_wrong_types_missing_and_extra_fields_fail(self):
        for payload in ({'id': 'x', 'vendor': 'V', 'amount': '100'}, {'id': 'x', 'vendor': 'V', 'amount': True},
                        {'id': 'x', 'vendor': 'V'}, {'id': 'x', 'vendor': 'V', 'amount': 100, 'extra': 1}):
            with self.subTest(payload=payload), self.assertRaises(ContractError):
                self.invoke('b.submit', 't.submit', payload)
        self.assertEqual(self.rows('applications'), [])

    def test_invalid_amount_and_unauthorized_or_self_approval(self):
        with self.assertRaises(ExecutionFailed):
            self.invoke('b.submit', 't.submit', {'id': 'x', 'vendor': 'V', 'amount': -1})
        self.submit()
        with self.assertRaises(PermissionError):
            self.invoke('b.approve', 't.approve', {'id': 'x', 'decision': True})
        with self.assertRaises(ExecutionFailed):
            self.invoke('b.approve', 't.approve', {'id': 'x', 'decision': True},
                        Principal('alice', frozenset({'role.approver'})))
        with self.assertRaises(ExecutionFailed):
            self.invoke('b.upload', 't.upload', {'id': 'x', 'file_a': 'A', 'file_b': 'B'},
                        Principal('mallory', frozenset({'role.requester'})))
        self.assertEqual(self.services.application('x')['status'], 'waiting-approval')

    def test_no_quote_branch_and_duplicate_confirmation_fail(self):
        self.submit()
        self.decide()
        with self.assertRaises(ExecutionFailed) as caught:
            self.invoke('b.confirm', 't.confirm', {'id': 'x'}, self.system)
        self.assertEqual(caught.exception.step_id, 's.stop')
        self.assertEqual(self.rows('orders'), [])

    def test_transaction_rolls_back_after_order_insert(self):
        self.submit()
        self.upload()
        self.decide()
        self.services.failures['confirm'] = ['after-insert']
        with self.assertRaises(ExecutionFailed):
            self.invoke('b.confirm', 't.confirm', {'id': 'x'}, self.system)
        self.assertEqual(self.rows('orders'), [])
        self.assertEqual(self.services.application('x')['status'], 'approved')
        self.invoke('b.confirm', 't.confirm', {'id': 'x'}, self.system)
        with self.assertRaises(ExecutionFailed):
            self.invoke('b.confirm', 't.confirm', {'id': 'x'}, self.system)
        self.assertEqual(len(self.rows('orders')), 1)

    def test_lock_conflict_and_release_after_failure(self):
        self.submit()
        with self.services.lock((('a.id', 'x'),)):
            with self.assertRaises(ExecutionFailed):
                self.upload('conflict')
        self.services.failures['put-B'] = ['before', 'before']
        with self.assertRaises(ExecutionFailed):
            self.upload('failed')
        self.upload('succeeds')
        self.assertEqual(len(self.rows('objects')), 2)

    def test_success_does_not_compensate_and_cannot_reuse_execution_id(self):
        self.submit()
        self.upload()
        self.assertEqual(self.services.calls, ['put-A', 'put-B'])
        with self.assertRaises(sqlite3.IntegrityError):
            self.upload()
        with self.assertRaises(ValueError):
            self.services.recover('upload')
        self.assertEqual(len(self.rows('objects')), 2)

    def test_first_upload_failure_never_executes_second(self):
        self.submit()
        self.services.failures['put-A'] = ['before', 'before']
        with self.assertRaises(ExecutionFailed):
            self.upload()
        self.assertNotIn('put-B', self.services.calls)
        self.assertEqual(self.rows('objects'), [])

    def test_second_upload_failure_compensates_reverse_order(self):
        self.submit()
        self.services.failures['put-B'] = ['before', 'before']
        with self.assertRaises(ExecutionFailed) as caught:
            self.upload()
        self.assertEqual(caught.exception.compensation_errors, [])
        self.assertEqual(self.services.calls[-2:], ['delete-B', 'delete-A'])
        self.assertEqual(self.rows('objects'), [])
        self.assertEqual(self.rows('attachments'), [])

    def test_transient_failure_and_lost_response_retries_are_idempotent(self):
        for point in ('before', 'after'):
            with self.subTest(point=point):
                services = Services(Path(self.tmp.name) / f'{point}.db')
                engine = Engine(self.program, registry, services, interfaces)
                self.invoke('b.submit', 't.submit', {'id': 'x', 'vendor': 'V', 'amount': 1}, engine=engine)
                services.failures['put-B'] = [point]
                self.invoke('b.upload', 't.upload', {'id': 'x', 'file_a': 'A', 'file_b': 'B'}, run_id='upload', engine=engine)
                with services.connect() as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM objects').fetchone()[0], 2)
                self.assertNotIn('delete-A', services.calls)

    def test_exhausted_lost_responses_remove_both_objects(self):
        self.submit()
        self.services.failures['put-B'] = ['after', 'after']
        with self.assertRaises(ExecutionFailed):
            self.upload()
        self.assertEqual(self.rows('objects'), [])

    def test_compensation_failure_persists_for_recovery_after_reopen(self):
        self.submit()
        self.services.failures['put-B'] = ['before', 'before']
        self.services.failures['delete-A'] = ['before']
        with self.assertRaises(ExecutionFailed) as caught:
            self.upload()
        self.assertEqual(caught.exception.compensation_errors[0][0], 'c.delete-a')
        self.assertEqual(next(r[1] for r in self.rows('runs') if r[0] == 'upload'), 'manual-recovery')
        self.assertEqual(len(self.rows('objects')), 1)
        reopened = Services(self.services.database)
        reopened.recover('upload')
        reopened.recover('upload')
        self.assertEqual(self.rows('objects'), [])

    def test_recovery_preserves_another_execution_or_version(self):
        self.submit()
        self.services.failures['put-B'] = ['before', 'before']
        self.services.failures['delete-A'] = ['before']
        with self.assertRaises(ExecutionFailed):
            self.upload()
        with self.services.connect() as db:
            db.execute("UPDATE objects SET owner='someone-else', version='new'")
        with self.assertRaises(ValueError):
            self.services.recover('upload')
        self.assertEqual(len(self.rows('objects')), 1)

    def test_interrupted_intent_can_be_reconciled_explicitly(self):
        self.services.begin('interrupted')
        self.services.put('interrupted', 'A', 'body')
        with self.assertRaises(ValueError):
            self.services.recover('interrupted')
        Services(self.services.database).recover('interrupted', interrupted=True)
        self.assertEqual(self.rows('objects'), [])

    def test_source_snapshots_match(self):
        self.assertEqual(interfaces_source(self.program), (ROOT / 'examples/purchase/interfaces.py').read_text())
        self.assertEqual(self.program.documentation(registry, details_link="../../docs/execution-design.md"), (ROOT / 'examples/purchase/requirements.md').read_text())

    def test_initial_generation_and_unimplemented_skeleton(self):
        initial = json.loads((ROOT / 'docs/requirements/purchase-initial.json').read_text())
        target = Path(self.tmp.name) / 'generated'
        initialize(initial, target)
        namespace = {}
        exec((target / 'handlers.py').read_text(), namespace)
        with self.assertRaises(NotImplementedError):
            namespace['registry'].handlers['s.submit'](Context({}, None, 'id', 'actor', []))
        with self.assertRaises(FileExistsError):
            initialize(initial, target)
        self.assertEqual((target / 'interfaces.py').read_text(), interfaces_source(Program(initial)))
        namespace = {}
        exec((target / 'contract.py').read_text(), namespace)
        self.assertEqual(namespace['SPEC'], initial)

    def test_interface_refresh_preserves_handwritten_implementation(self):
        import subprocess
        import sys
        target = Path(self.tmp.name) / 'generated'
        initial = json.loads((ROOT / 'docs/requirements/purchase-initial.json').read_text())
        initialize(initial, target)
        implementation = target / 'handlers.py'
        implementation.write_text('# handwritten implementation must survive\n')
        before = implementation.read_bytes()
        subprocess.run([sys.executable, '-m', 'myworkflow.scaffold', 'interfaces',
                        'examples.purchase.contract', str(target / 'interfaces.py')], cwd=ROOT, check=True)
        self.assertEqual(implementation.read_bytes(), before)
        self.assertEqual((target / 'interfaces.py').read_text(), interfaces_source(self.program))

    def test_missing_implementation_and_bad_signature_detected(self):
        missing = registry.fork()
        missing.remove('s.confirm')
        with self.assertRaisesRegex(ContractError, 's.confirm'):
            self.program.check(missing)
        with self.assertRaisesRegex(ContractError, 's.invalid'):
            missing.implements('s.invalid')(lambda ctx: None)

    def test_output_and_undeclared_writes_detected(self):
        for wrong in ('type', 'extra'):
            modified = registry.fork()
            @modified.implements('s.test')
            def invalid(ctx: Context) -> None:
                ctx.values['status'] = 123 if wrong == 'type' else 'waiting-approval'
                if wrong == 'extra':
                    ctx.values['secret'] = 'undeclared'
            modified.replace('s.submit', modified.handlers['s.test'])
            engine = Engine(self.program, modified, self.services, interfaces)
            with self.subTest(wrong=wrong), self.assertRaises(ExecutionFailed) as caught:
                self.invoke('b.submit', 't.submit', {'id': f'x-{wrong}', 'vendor': 'V', 'amount': 1}, engine=engine)
            self.assertIsInstance(caught.exception.cause, ContractError)

    def test_unknown_target_missing_branch_and_reordered_steps_detected(self):
        for mutate in ('target', 'mapping', 'branch', 'order', 'next-workflow', 'unknown-condition'):
            spec = copy.deepcopy(SPEC)
            if mutate == 'target':
                spec['workflows'][0]['bindings'][0]['pipeline'] = 'missing'
            elif mutate == 'mapping':
                spec['workflows'][0]['bindings'][0]['triggers'][0]['mapping'].pop('a.id')
            elif mutate == 'unknown-condition':
                spec['pipelines'][2]['steps'][2]['when'] = ['missing', True]
            elif mutate == 'next-workflow':
                spec['workflows'][0]['bindings'][2]['next_workflow'] = 'missing'
            elif mutate == 'branch':
                spec['pipelines'][2]['steps'].pop()
            else:
                steps = spec['pipelines'][4]['steps']
                steps[1], steps[2] = steps[2], steps[1]
            with self.subTest(mutate=mutate), self.assertRaises((ContractError, ValueError)):
                Program(spec)

    def test_stale_interface_and_required_input_change(self):
        spec = copy.deepcopy(SPEC)
        spec['artifacts'].append(dict(id='a.department', key='department', name='依頼部門', type='str'))
        spec['pipelines'][0]['inputs'].append('a.department')
        spec['workflows'][0]['bindings'][0]['triggers'][0]['mapping']['a.department'] = 'department'
        changed = Program(spec)
        with self.assertRaisesRegex(ContractError, 'p.submit'):
            Engine(changed, registry, self.services, interfaces)
        generated = SimpleNamespace()
        exec(interfaces_source(changed), generated.__dict__)
        updated_registry = registry.fork()
        # Extend both the step contract and implementation for the new requirement.
        spec['pipelines'][0]['steps'][1]['reads'].append('a.department')
        changed = Program(spec)
        seen_departments = []
        @updated_registry.implements('s.department-submit')
        def department_submit(ctx: Context) -> None:
            if not ctx.values['department'].strip():
                raise ValueError('Department is required')
            seen_departments.append(ctx.values['department'])
            registry.handlers['s.submit'](ctx)
        updated_registry.replace('s.submit', updated_registry.handlers['s.department-submit'])
        engine = Engine(changed, updated_registry, self.services, generated)
        with self.assertRaises(ContractError):
            self.invoke('b.submit', 't.submit', {'id': 'x', 'vendor': 'V', 'amount': 1}, engine=engine)
        result = self.invoke('b.submit', 't.submit', {'id': 'x', 'vendor': 'V', 'amount': 1, 'department': '営業'}, engine=engine)
        self.assertEqual(result.status, 'waiting-approval')
        self.assertEqual(seen_departments, ['営業'])
        self.assertIn('依頼部門', changed.documentation())
        self.assertEqual(spec['pipelines'][0]['steps'][1]['id'], 's.submit')

    def test_generated_output_type_drift_and_undeclared_read(self):
        import dataclasses
        changed = SimpleNamespace(**vars(interfaces))
        changed.PSubmitResponse = dataclasses.make_dataclass('WrongResponse', [('application_id', str), ('status', int)])
        with self.assertRaisesRegex(ContractError, 'p.submit'):
            Engine(self.program, registry, self.services, changed)
        modified = registry.fork()
        @modified.implements('s.read-test')
        def invalid_read(ctx: Context) -> None:
            ctx.values['decision']
        modified.replace('s.submit', modified.handlers['s.read-test'])
        with self.assertRaises(ExecutionFailed) as caught:
            self.invoke('b.submit', 't.submit', {'id': 'x', 'vendor': 'V', 'amount': 1},
                        engine=Engine(self.program, modified, self.services, interfaces))
        self.assertIsInstance(caught.exception.cause, ContractError)
        self.assertIn('undeclared context read', str(caught.exception.cause))

    def test_recovery_after_abrupt_process_exit(self):
        import subprocess
        import sys
        code = "from examples.purchase.services import Services; import os,sys; s=Services(sys.argv[1]); s.begin('crashed'); s.put('crashed','A','body'); os._exit(17)"
        result = subprocess.run([sys.executable, '-c', code, self.services.database], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 17, result.stderr.decode())
        self.assertEqual(len(self.rows('objects')), 1)
        Services(self.services.database).recover('crashed', interrupted=True)
        self.assertEqual(self.rows('objects'), [])

    def test_rename_trigger_change_and_approval_role_change(self):
        spec = copy.deepcopy(SPEC)
        spec['artifacts'][0]['name'] = '購買依頼番号'
        spec['workflows'][0]['bindings'][1]['triggers'][0]['role'] = 'role.buyer'
        spec['workflows'][0]['bindings'][0]['triggers'].append(dict(
            id='t.import', name='申請取込', role='role.requester',
            mapping={'a.id': 'number', 'a.vendor': 'supplier', 'a.amount': 'total'}))
        changed = Program(spec)
        engine = Engine(changed, registry, self.services, interfaces)
        self.invoke('b.submit', 't.import', {'number': 'x', 'supplier': 'V', 'total': 1}, engine=engine)
        with self.assertRaises(PermissionError):
            self.invoke('b.approve', 't.approve', {'id': 'x', 'decision': True}, self.approver, engine=engine)
        self.invoke('b.approve', 't.approve', {'id': 'x', 'decision': True},
                    Principal('buyer', frozenset({'role.buyer'})), engine=engine)
        text = changed.documentation(registry)
        self.assertIn('購買依頼番号', text)
        self.assertIn('w.approval/b.submit/p.submit/s.submit', text)
        self.assertIn('トリガー2：申請取込', text)
