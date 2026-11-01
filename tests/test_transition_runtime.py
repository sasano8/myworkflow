"""Transition enforcement at the pipeline/optimistic commit boundary."""
from dataclasses import replace

import pytest

from examples.approval_values import application as sample
from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.artifact_jobs import ArtifactConflict, ArtifactWrite, JobState
from myworkflow.errors import ContractError, ExecutionFailed
from myworkflow.executable import Context, Principal
from myworkflow.runtime.changes import Changes
from myworkflow.runtime.transitions import TransitionRuntime


@pytest.fixture
def coordinator(tmp_path):
    provider = TemporaryArtifactCoordinator(tmp_path, namespace='transitions')
    sample.seed(provider)
    return provider


@pytest.fixture
def runner(coordinator, tmp_path):
    return sample.engine(coordinator, tmp_path / 'runs.sqlite')


def invoke(runner, *, actor='bob', roles=None, run_id='approve'):
    principal = Principal(actor, frozenset({sample.reviewer.id}) if roles is None else roles)
    return runner.invoke_or_raise(sample.Approval.execute, sample.Approval.requested,
                                  {'id': 'example'}, principal, run_id=run_id)


def change_handler(coordinator, tmp_path, fn):
    handlers = sample.registry.fork()
    handlers.replace(sample.record_approval, fn)
    return sample.engine(coordinator, tmp_path / 'runs.sqlite', handlers=handlers)


def test_plain_updates_follow_transition_and_preserve_read_version(runner, coordinator):
    result = invoke(runner)
    assert result.ok
    record = coordinator.read('application:example')
    assert record.value == {'owner': 'alice', 'amount': 100, 'approved_by': 'bob',
                            'status': sample.Approval.approved.id}
    assert record.version == 2
    assert coordinator.status('approve').state == JobState.COMMITTED
    with pytest.raises(ExecutionFailed, match='eligible transition'):
        invoke(runner, run_id='approve-again')
    assert coordinator.status('approve-again') is None


def test_role_and_guard_rejections_do_not_change_data(runner, coordinator):
    with pytest.raises(PermissionError):
        invoke(runner, roles=frozenset())
    with pytest.raises(ExecutionFailed, match='eligible transition'):
        invoke(runner, actor='alice', run_id='self-approval')
    assert coordinator.status('approve') is None
    assert coordinator.status('self-approval') is None
    assert coordinator.read('application:example').version == 1


@pytest.mark.parametrize('target', ['invented-state', None])
def test_wrong_or_missing_target_rejects_entire_change_set(coordinator, tmp_path, target):
    coordinator.prepare('seed-extra', (ArtifactWrite('extra', {'count': 0}),))
    coordinator.commit('seed-extra')
    def handler(ctx: Context) -> None:
        ctx.changes.update(ctx.changes.read('extra'), count=1)
        fields = {'approved_by': ctx.actor}
        if target is not None:
            fields['status'] = target
        ctx.changes.update(ctx.changes.subject, **fields)
    runner = change_handler(coordinator, tmp_path, handler)
    with pytest.raises(ExecutionFailed, match='declared target'):
        invoke(runner)
    assert coordinator.status('approve') is None
    assert coordinator.read('extra').value['count'] == 0
    assert coordinator.read('application:example').version == 1


def test_business_failure_does_not_prepare_staged_changes(coordinator, tmp_path):
    def handler(ctx: Context) -> None:
        sample.approve(ctx)
        raise ValueError('business operation failed')
    runner = change_handler(coordinator, tmp_path, handler)
    with pytest.raises(ExecutionFailed, match='business operation failed'):
        invoke(runner)
    assert coordinator.status('approve') is None
    assert coordinator.read('application:example').version == 1


def test_direct_pipeline_entries_cannot_bypass_transition_or_roles(runner, coordinator):
    for run in (runner.run, runner.run_internal):
        assert not run(sample.approval, {'application_id': 'example'}, actor='bob', run_id='bypass').ok
    with pytest.raises(ContractError, match='authorized trigger'):
        runner.run_or_raise(sample.approval, {'application_id': 'example'}, actor='bob', run_id='bypass')
    assert coordinator.read('application:example').version == 1


def test_stale_version_rejects_all_writes(coordinator, tmp_path):
    coordinator.prepare('seed-extra', (ArtifactWrite('extra', {'count': 0}),))
    coordinator.commit('seed-extra')
    def handler(ctx: Context) -> None:
        sample.approve(ctx)
        ctx.changes.update(ctx.changes.read('extra'), count=1)
        original = coordinator.read('application:example')
        coordinator.prepare('concurrent', (ArtifactWrite(original.key, {**original.value, 'amount': 999}, original.version),))
        coordinator.commit('concurrent')
    runner = change_handler(coordinator, tmp_path, handler)
    with pytest.raises(ExecutionFailed) as caught:
        invoke(runner)
    assert isinstance(caught.value.cause, ArtifactConflict)
    assert coordinator.read('application:example').value['amount'] == 999
    assert coordinator.read('application:example').value['status'] == sample.Approval.waiting.id
    assert coordinator.read('extra').value['count'] == 0
    assert coordinator.status('approve').state == JobState.PREPARED


def test_guard_requires_bool_and_ambiguity_is_rejected_before_handler(coordinator, tmp_path):
    original = sample.compiled.graphs[0]
    for transitions, message in (
        ((replace(original.transitions[0], guard=lambda ctx: 'yes'),), 'must return bool'),
        ((*original.transitions, replace(original.transitions[0], id='tr.other')), 'got 2'),
        ((), 'got 0'),
    ):
        graph = replace(original, transitions=transitions)
        # Empty transition graphs would make the approved state unreachable.
        if not transitions:
            graph = replace(graph, states=(original.initial,))
        compiled = replace(sample.compiled, graphs=(graph,))
        adapter = TransitionRuntime(compiled, graph, coordinator, key=lambda values: 'application:example')
        runner = sample.engine(coordinator, tmp_path / (str(len(transitions)) + '.sqlite'))
        runner.transitions = adapter
        with pytest.raises(ExecutionFailed, match=message):
            invoke(runner)
    assert coordinator.read('application:example').version == 1


def test_documented_condition_without_guard_fails_closed(coordinator):
    original = sample.compiled.graphs[0]
    graph = replace(original, transitions=(replace(original.transitions[0], guard=None),))
    compiled = replace(sample.compiled, graphs=(graph,))
    with pytest.raises(ContractError, match='executable guard'):
        TransitionRuntime(compiled, graph, coordinator, key=lambda values: 'application:example')


def test_record_handles_are_local_and_reads_do_not_mutate_stored_or_staged_values(coordinator):
    first, second = Changes(coordinator), Changes(coordinator)
    record = first.read('application:example')
    record.value['status'] = 'invalid'
    assert first.read(record.key).value['status'] == sample.Approval.waiting.id
    with pytest.raises(ContractError, match='read by this'):
        second.update(record, status='invalid')
    first._close()
    with pytest.raises(ContractError, match='closed'):
        first.update(record, status='invalid')


def test_commit_response_loss_preserves_changes_for_reconciliation(coordinator, tmp_path):
    class LostResponse:
        def __getattr__(self, name):
            return getattr(coordinator, name)
        def commit(self, job_id):
            coordinator.commit(job_id)
            raise OSError('commit response lost')
    runner = sample.engine(LostResponse(), tmp_path / 'runs.sqlite')
    with pytest.raises(ExecutionFailed) as caught:
        invoke(runner)
    assert caught.value.secondary_errors[0][0] == 'transition-recovery'
    assert coordinator.status('approve').state == JobState.COMMITTED
    assert coordinator.read('application:example').value['status'] == sample.Approval.approved.id


def test_prepare_and_commit_stop_retains_validated_writes(coordinator, tmp_path):
    class Stopped:
        def __getattr__(self, name):
            return getattr(coordinator, name)
        def commit(self, job_id):
            raise OSError('worker stopped')
    runner = sample.engine(Stopped(), tmp_path / 'runs.sqlite')
    with pytest.raises(ExecutionFailed):
        invoke(runner)
    assert coordinator.status('approve').state == JobState.PREPARED
    assert coordinator.read('application:example').value['status'] == sample.Approval.waiting.id
    coordinator.commit('approve')
    assert coordinator.read('application:example').value['status'] == sample.Approval.approved.id



def test_concurrent_transitions_have_one_winner(coordinator, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    barrier = Barrier(2)
    def handler(ctx: Context) -> None:
        sample.approve(ctx)
        barrier.wait(timeout=5)
    runner = change_handler(coordinator, tmp_path, handler)
    def run(number):
        try:
            return invoke(runner, run_id=f'parallel-{number}').ok
        except ExecutionFailed as exc:
            assert isinstance(exc.cause, ArtifactConflict)
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, (1, 2))) == [False, True]
    assert coordinator.read('application:example').version == 2


def test_journal_failure_after_commit_does_not_compensate_business_data(coordinator, tmp_path):
    from myworkflow.executable import Engine
    from myworkflow.pipeline_declarations import Operation
    from myworkflow.ports import RunStatus
    pipeline = sample.compiled.catalog.pipelines[0]
    step = replace(pipeline.steps[0], compensate='compensate.approval')
    catalog = replace(sample.compiled.catalog, pipelines=(replace(pipeline, steps=(step,)),))
    from myworkflow.program import Program
    program = Program.from_catalog(catalog)
    compiled = replace(sample.compiled, program=program)
    called = []
    handlers = sample.registry.fork()
    @handlers.implements(Operation('compensate.approval'))
    def compensate(ctx: Context) -> None:
        called.append('compensated')
    class FailedJournal:
        status = None
        def begin(self, run_id):
            pass
        def record(self, run_id, events, status):
            if status == RunStatus.COMPLETED:
                raise OSError('journal failed after commit')
            self.status = status
    journal = FailedJournal()
    runtime = TransitionRuntime(compiled, compiled.graphs[0], coordinator, key=lambda values: 'application:example')
    runner = Engine(program, handlers, None, store=journal, transitions=runtime)
    with pytest.raises(ExecutionFailed, match='journal failed'):
        invoke(runner)
    assert called == []
    assert journal.status == RunStatus.MANUAL_RECOVERY
    assert coordinator.status('approve').state == JobState.COMMITTED


def test_saved_graph_keeps_guard_function_reference():
    model = sample.compiled.graphs[0].to_dict(sample.compiled.catalog)
    assert model['transitions'][0]['guard'] == 'examples.approval_values.application:may_approve'
    assert sample.compiled.graphs[0].transitions[0].guard is sample.may_approve
    from myworkflow.build import BuildConfig, compile_outputs
    import json
    ir = json.loads(compile_outputs(BuildConfig(sample.compiled, sample.registry), target='temporal')['ir.json'])
    assert ir['state_graphs'][0]['transitions'][0]['guard'] == model['transitions'][0]['guard']



def test_non_function_guard_is_rejected_before_ir_export(coordinator):
    class CallableGuard:
        def __call__(self, ctx):
            return True
    original = sample.compiled.graphs[0]
    graph = replace(original, transitions=(replace(original.transitions[0], guard=CallableGuard()),))
    compiled = replace(sample.compiled, graphs=(graph,))
    with pytest.raises(ContractError, match='Python function'):
        TransitionRuntime(compiled, graph, coordinator, key=lambda values: 'application:example')
