"""Static discovery, refactorable references and integration with the existing runtime."""
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

from examples.feature_demos.declarative_review import contract as sample
from myworkflow import Artifact, ContractCatalog, Lock, Pipeline, Role, Step
from myworkflow.codegen import interfaces_source
from myworkflow.declarations import bind, compile_workflows, state, transition, trigger, workflow
from myworkflow.errors import ContractError
from myworkflow.executable import Context, Engine, Principal, Program, Registry
from myworkflow.adapters.sqlite import SQLiteDatabase, SQLiteExecutionStore
from myworkflow.quality.business import export_business

ROOT = Path(__file__).resolve().parents[1]


def test_sample_matches_reviewable_output_and_existing_program():
    compiled = sample.compiled
    assert sample.documentation() == (ROOT / 'examples/feature_demos/declarative_review/docs/requirements.md').read_text()
    assert compiled.catalog.workflows[0] is compiled.graphs[0].workflow
    assert compiled.catalog.pipelines == (sample.submit_application, sample.record_review)
    assert len(compiled.graphs[0].transitions) == 5
    assert len(compiled.catalog.workflows[0].bindings[1].triggers) == 3
    assert export_business(Program(compiled.program.spec)) == export_business(compiled.program)
    snapshot = compiled.program.spec
    snapshot['workflows'][0]['name'] = '改変'
    assert compiled.program.model.workflows[0].name == '申請内容の審査と再申請'


def test_identifier_rename_keeps_export_connections_and_ids():
    source = (ROOT / 'examples/feature_demos/declarative_review/contract.py').read_text()
    # Change Python symbols only. Stable IDs deliberately keep the old spelling.
    import io
    import tokenize
    names = {'ApplicationReview': 'RenamedReview', 'pending': 'awaiting_review',
             'review': 'review_placement', 'approval': 'approval_event', 'submit_application': 'receive_application'}
    tokens = [t._replace(string=names[t.string]) if t.type == tokenize.NAME and t.string in names else t
              for t in tokenize.generate_tokens(io.StringIO(source).readline)]
    module = ModuleType('renamed_review')
    exec(compile(tokenize.untokenize(tokens), 'renamed_review.py', 'exec'), module.__dict__)
    assert export_business(module.program) == export_business(sample.program)
    assert module.compiled.graphs[0].to_dict(module.compiled.catalog) == sample.compiled.graphs[0].to_dict(sample.compiled.catalog)
    assert module.documentation() == sample.documentation()


def minimal(*, initial_count=1):
    role = Role('role.test', '操作担当者', '担当者')
    pipeline = Pipeline('p.test', '検査', (), (), ())

    @workflow(id='w.test', name='検査業務')
    class Flow:
        start = state('state.start', '開始', initial=initial_count > 0)
        end = state('state.end', '完了', initial=initial_count > 1)
        event = trigger('t.test', '実行操作', role)
        task = bind('b.test', pipeline, (event,), (('system', role),))
        finish = transition('tr.test', '完了させる', start, end, task, event)
    return Flow


def test_discovery_does_not_call_methods_or_properties():
    flow = minimal()
    def forbidden(*args):
        raise AssertionError('discovery executed application code')
    flow.hidden = property(forbidden)
    flow.handler = forbidden
    assert len(compile_workflows(flow).graphs[0].transitions) == 1


@pytest.mark.parametrize('count', [0, 2])
def test_exactly_one_initial_state(count):
    with pytest.raises(ContractError, match='exactly one initial'):
        compile_workflows(minimal(initial_count=count))


@pytest.mark.parametrize('mutation, message', [
    (lambda f: setattr(f, 'alias', f.start), 'aliases'),
    (lambda f: setattr(f, 'start', replace(f.start, initial=1)), 'initial must be boolean'),
    (lambda f: setattr(f, 'finish', replace(f.finish, source=replace(f.start))), 'undeclared source'),
    (lambda f: setattr(f, 'finish', replace(f.finish, binding=replace(f.task))), 'binding must reference'),
    (lambda f: setattr(f, 'finish', replace(f.finish, trigger=replace(f.event))), 'trigger must reference'),
    (lambda f: setattr(f, 'task', replace(f.task, triggers=())), 'distinct trigger'),
    (lambda f: setattr(f, 'task', replace(f.task, triggers=[f.event])), 'tuple of TriggerDeclaration'),
    (lambda f: setattr(f, 'task', replace(f.task, pipeline='p.test')), 'Pipeline reference'),
    (lambda f: setattr(f, 'task', replace(f.task, roles=(('system', 'role.test'),))), 'Role reference'),
    (lambda f: setattr(f, 'task', replace(f.task, next_workflow=minimal())), 'included in compilation'),
])
def test_invalid_symbolic_declarations(mutation, message):
    flow = minimal()
    mutation(flow)
    with pytest.raises(ContractError, match=message):
        compile_workflows(flow)


def test_artifact_mapping_rejects_copied_or_string_reference():
    artifact = Artifact('a.value', '値', 'value', 'str')
    for reference in (replace(artifact), artifact.id):
        flow = minimal()
        altered = replace(flow.event, mapping=((reference, 'value'),))
        flow.task = replace(flow.task, triggers=(altered,))
        with pytest.raises(ContractError, match='declared Artifact object'):
            compile_workflows(flow, artifacts=(artifact,))


def test_class_requirements_and_inheritance():
    with pytest.raises(ContractError, match='decorated'):
        compile_workflows(type('Undecorated', (), {}))
    with pytest.raises(ContractError, match='class'):
        workflow(id='w.bad', name='不正')(lambda: None)
    with pytest.raises(ContractError, match='inheritance'):
        workflow(id='w.child', name='継承')(type('Child', (minimal(),), {}))
    with pytest.raises(ContractError, match='duplicate class'):
        flow = minimal()
        compile_workflows(flow, flow)


def test_cross_workflow_link_and_global_state_ids():
    following = minimal()
    starting = minimal()
    starting.__workflow_options__ = replace(starting.__workflow_options__, id='w.before')
    # Independent names/IDs, but one shared pipeline and role declaration for reuse.
    starting.start = state('state.before_start', '開始', initial=True)
    starting.end = state('state.before_end', '完了')
    starting.event = replace(following.event, id='t.before')
    starting.task = bind('b.before', following.task.pipeline, (starting.event,), following.task.roles,
                         next_workflow=following)
    starting.finish = transition('tr.before', '引継ぎ', starting.start, starting.end, starting.task, starting.event)
    result = compile_workflows(starting, following)
    assert result.program.next_binding('b.before', 'b.test').id == 'b.test'
    assert len(result.catalog.pipelines) == 1
    following.end = replace(following.end, id='state.before_end')
    following.finish = replace(following.finish, target=following.end)
    with pytest.raises(ContractError, match='globally unique'):
        compile_workflows(starting, following)


def test_generated_interfaces_and_compiled_pipeline_execute(tmp_path):
    compiled = sample.compiled
    registry = Registry()
    observed = []
    @registry.implements('s.review_submit')
    def receive(ctx: Context) -> None:
        observed.append(ctx.values['application_id'])
    @registry.implements('s.review_record')
    def record(ctx: Context) -> None:
        observed.append(ctx.values['application_id'])
    interfaces = ModuleType('review_interfaces')
    exec(interfaces_source(compiled.program), interfaces.__dict__)
    store = SQLiteExecutionStore(SQLiteDatabase(tmp_path / 'runs.sqlite'))
    engine = Engine(compiled.program, registry, None, interfaces, store=store)
    response = engine.invoke_or_raise('b.review_submit', 't.review_submit', {'id': 'application-1'},
                             Principal('alice', frozenset({'role.requester'})), run_id='run-1')
    assert response.code == 0
    assert observed == ['application-1']
    assert store.get('run-1')[0] == 'completed'
    with pytest.raises(PermissionError):
        engine.invoke_or_raise('b.review_record', 't.review_approve', {'id': 'application-1', 'decision': 'approve'},
                      Principal('alice', frozenset({'role.requester'})), run_id='run-2')
    # This invokes a pipeline only; state graph execution/guard enforcement is intentionally absent.


def test_typed_catalog_export_preserves_lock_metadata_and_compensation():
    from myworkflow import Binding, Workflow
    artifact = Artifact('a.key', '対象ID', 'key', 'str')
    role = Role('role.system', 'システム', 'システム')
    pipeline = Pipeline('p.locked', '排他実行', (artifact.id,), (artifact.id,), (
        Lock('s.locked', '対象排他', (artifact.id,), scope='処理終了まで', namespace='test', timeout=1, conflict='待機'),
        Step('s.operation', '処理', '対象を処理する。', reads=(artifact.id,), compensate='undo.operation'),
    ))
    binding = Binding('b.locked', pipeline.id, '操作', ((artifact.id, 'id'),),
                      actor_role_id=role.id, role_mapping=(('system', role.id),), trigger_id='t.locked')
    catalog = ContractCatalog((artifact,), (pipeline,), (Workflow('w.locked', '排他業務', (binding,)),), (role,))
    typed = Program.from_catalog(catalog)
    assert typed.model is catalog
    assert typed.plans[pipeline.id] is pipeline
    assert export_business(typed) == export_business(Program(typed.spec))
    assert Program(typed.spec).plans[pipeline.id].steps[0].scope == '処理終了まで'
    with pytest.raises(ContractError, match='unique'):
        Program.from_catalog(replace(catalog, pipelines=(pipeline, pipeline)))


def test_different_objects_sharing_pipeline_id_are_rejected():
    first, second = minimal(), minimal()
    second.__workflow_options__ = replace(second.__workflow_options__, id='w.second')
    with pytest.raises(ContractError, match='different objects share'):
        compile_workflows(first, second)


def test_preceding_placement_and_wait_are_symbolic():
    flow = minimal()
    later_event = replace(flow.event, id='t.later', after=flow.task, wait='翌営業日')
    flow.later = bind('b.later', flow.task.pipeline, (later_event,), flow.task.roles)
    compiled = compile_workflows(flow)
    event = compiled.program.trigger('b.later', 't.later')
    assert event.after == flow.task.id
    assert event.wait == '翌営業日'
    flow.later = replace(flow.later, triggers=(replace(later_event, after=replace(flow.task)),))
    with pytest.raises(ContractError, match='preceding placement'):
        compile_workflows(flow)


def test_compiled_snapshot_is_independent_of_subsequent_class_edits():
    flow = minimal()
    compiled = compile_workflows(flow)
    previous = compiled.graphs[0].to_dict(compiled.catalog)
    flow.start = replace(flow.start, name='変更後')
    assert compiled.graphs[0].to_dict(compiled.catalog) == previous
    # A new compilation detects a stale transition reference rather than reconnecting by ID.
    with pytest.raises(ContractError, match='undeclared source'):
        compile_workflows(flow)


def test_typed_program_rejects_mutable_nested_declarations():
    catalog = sample.compiled.catalog
    pipeline = replace(catalog.pipelines[0], steps=list(catalog.pipelines[0].steps))
    with pytest.raises(ContractError, match='immutable values'):
        Program.from_catalog(replace(catalog, pipelines=(pipeline, *catalog.pipelines[1:])))
