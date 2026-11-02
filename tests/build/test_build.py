"""Deterministic build outputs and strict capability rejection without deployment."""
from dataclasses import replace
import io
import json
from pathlib import Path
import subprocess
import sys
import tokenize
from types import ModuleType

import pytest

from examples.apps.purchase import contract as purchase
from examples.apps.purchase.build import BUILD
from examples.apps.purchase.handlers import registry
from myworkflow import annotate, Artifact, Role
from myworkflow.build import BuildConfig, BuildError, build, compile_outputs
from myworkflow.compiler.declarations import bind, compile_workflows, state, transition, trigger, WorkflowDeclaration
from myworkflow.contracts.errors import ContractError
from myworkflow.executable import Context, Registry
from myworkflow.compiler.pipelines import Action, Mutex, Operation, PipelineDeclaration
from myworkflow.generation.business import export_business

ROOT = Path(__file__).resolve().parents[2]


def test_temporal_build_validates_code_without_generating_another_runtime():
    outputs = compile_outputs(BUILD, target='temporal')
    assert set(outputs) == {'ir.json', 'requirements.md', 'interfaces.py', 'build.json', 'data-definitions.md', 'data-definitions.json'}
    assert json.loads(outputs['ir.json'])['business'] == export_business(purchase.program)
    assert json.loads(outputs['build.json'])['mode'] == 'application-owned-code'
    assert outputs == compile_outputs(BUILD, target='temporal')


def test_kestra_preview_matches_frozen_yaml_and_declared_ids():
    outputs = compile_outputs(BUILD, target='kestra', workflows=('w.attach',))
    assert outputs['manifest.yaml'] == (ROOT / 'examples/apps/purchase/docs/kestra-attachment.yaml').read_text()
    model = json.loads(outputs['ir.json'])
    assert list(model['business']['workflows']) == ['w.attach']
    assert list(model['business']['pipelines']) == ['p.upload']
    assert set(model['implementations']) == {'s.check-upload', 's.put-a', 's.put-b', 'c.delete-a', 'c.delete-b'}
    assert json.loads(outputs['build.json'])['mode'] == 'preview'


def test_unsupported_purchase_control_flow_fails_before_writing(tmp_path):
    sentinel = tmp_path / 'manifest.yaml'
    sentinel.write_text('keep this')
    with pytest.raises(BuildError) as caught:
        build(BUILD, tmp_path, target='kestra')
    assert 'w.approval/b.approve/t.approve: wait' in str(caught.value)
    assert 'next_workflow' in str(caught.value)
    assert sentinel.read_text() == 'keep this'
    assert set(tmp_path.iterdir()) == {sentinel}


def test_check_mode_detects_drift_without_rewriting(tmp_path):
    build(BUILD, tmp_path, target='kestra', workflows=('w.attach',))
    build(BUILD, tmp_path, target='kestra', workflows=('w.attach',), check=True)
    target = tmp_path / 'manifest.yaml'
    target.write_text('manually changed')
    with pytest.raises(ValueError, match='stale'):
        build(BUILD, tmp_path, target='kestra', workflows=('w.attach',), check=True)
    assert target.read_text() == 'manually changed'


@pytest.mark.parametrize('change, message', [
    ({'target': 'unknown'}, 'Unknown target'),
    ({'target': 'kestra', 'workflows': ('missing',)}, 'Unknown workflows'),
    ({'target': 'temporal', 'workflows': ('w.approval',)}, 'outside the explicit selection'),
])
def test_invalid_build_selections(change, message):
    with pytest.raises(BuildError, match=message):
        compile_outputs(BUILD, **change)


def test_unknown_guarantee_and_missing_implementation_fail():
    with pytest.raises(BuildError, match='distributed_lock'):
        compile_outputs(replace(BUILD, required_features=('distributed_lock',)), target='kestra')
    missing = registry.fork()
    missing.remove(purchase.save_quote_b)
    with pytest.raises(ContractError, match='s.put-b'):
        compile_outputs(replace(BUILD, registry=missing), target='kestra', workflows=('w.attach',))


def test_target_switch_cannot_leave_a_stale_manifest(tmp_path):
    build(BUILD, tmp_path, target='kestra', workflows=('w.attach',))
    previous = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(BuildError, match='separate output directory'):
        build(BUILD, tmp_path, target='temporal')
    assert previous == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_cli_build_check_and_unsupported_exit_codes(tmp_path):
    base = [sys.executable, '-m', 'myworkflow', 'build', '--config', 'examples.apps.purchase.build', '--target', 'kestra',
            '--output', str(tmp_path / 'valid')]
    success = subprocess.run([*base, '--workflow', 'w.attach'], cwd=ROOT, capture_output=True, text=True)
    assert success.returncode == 0, success.stderr
    assert 'not deployable' in success.stdout
    checked = subprocess.run([*base, '--workflow', 'w.attach', '--check'], cwd=ROOT, capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr
    failed = subprocess.run([*base[:-1], str(tmp_path / 'unsupported')], cwd=ROOT, capture_output=True, text=True)
    assert failed.returncode == 1
    assert 'wait is not supported' in failed.stderr
    assert not (tmp_path / 'unsupported').exists()


def symbolic_example(*, with_states=False, with_after=False):
    value = Artifact('a.value', '値', 'value', 'str')
    role = Role('role.operator', '担当者', '担当者')
    undo = Operation('c.undo')
    action = Action('s.save', '保存', '保存する。', reads=(value,), compensate=undo)
    pipeline = PipelineDeclaration('p.save', '保存', (value,), (), (action,))
    @annotate(WorkflowDeclaration(id='w.save', name='保存フロー'))
    class Flow:
        event = trigger('t.save', '保存操作', role, ((value, 'value'),))
        save = bind('b.save', pipeline, (event,), (('system', role),))
    if with_states:
        Flow.start = state('state.start', '開始', initial=True)
        Flow.end = state('state.end', '完了')
        Flow.finish = transition('tr.finish', '完了', Flow.start, Flow.end, Flow.save, Flow.event)
    if with_after:
        Flow.later_event = trigger('t.later', '後続', role, ((value, 'value'),), after=Flow.save)
        Flow.later = bind('b.later', pipeline, (Flow.later_event,), (('system', role),))
    definitions = Registry()
    @definitions.implements(action)
    def save(ctx: Context) -> None: pass
    @definitions.implements(undo)
    def compensate(ctx: Context) -> None: pass
    return value, action, pipeline, Flow, definitions


@pytest.mark.parametrize('feature, message', [('with_states', 'state graph execution'), ('with_after', 'after is not supported')])
def test_unsupported_graph_or_dependency_is_not_silently_dropped(feature, message):
    value, _, _, flow, implementations = symbolic_example(**{feature: True})
    config = BuildConfig(compile_workflows(flow, artifacts=(value,)), implementations)
    with pytest.raises(BuildError, match=message):
        compile_outputs(config, target='kestra')


@pytest.mark.parametrize('mutation', ['copied-input', 'string-read', 'string-compensation', 'duplicate-input'])
def test_symbolic_pipeline_requires_real_references(mutation):
    value, action, pipeline, flow, _ = symbolic_example()
    if mutation == 'copied-input':
        pipeline = replace(pipeline, inputs=(replace(value),))
    elif mutation == 'string-read':
        pipeline = replace(pipeline, steps=(replace(action, reads=(value.id,)),))
    elif mutation == 'string-compensation':
        pipeline = replace(pipeline, steps=(replace(action, compensate='c.undo'),))
    else:
        pipeline = replace(pipeline, inputs=(value, value))
    flow.save = replace(flow.save, pipeline=pipeline)
    with pytest.raises(ContractError):
        compile_workflows(flow, artifacts=(value,))


def test_purchase_identifier_rename_preserves_ir_and_compensation_connections():
    source = (ROOT / 'examples/apps/purchase/contract.py').read_text()
    replacements = {'application_id': 'purchase_identity', 'save_quote_a': 'persist_first_quote',
                    'delete_quote_a': 'undo_first_quote', 'PurchaseAttachment': 'QuotationAttachment'}
    tokens = [token._replace(string=replacements[token.string]) if token.type == tokenize.NAME and token.string in replacements else token
              for token in tokenize.generate_tokens(io.StringIO(source).readline)]
    module = ModuleType('renamed_purchase')
    # Register for dataclass/inspect support while loading an independent declaration module.
    sys.modules[module.__name__] = module
    try:
        exec(compile(tokenize.untokenize(tokens), 'renamed_purchase.py', 'exec'), module.__dict__)
        assert export_business(module.program) == export_business(purchase.program)
        assert module.persist_first_quote.compensate is module.undo_first_quote
        assert module.compiled.workflow(module.QuotationAttachment).id == 'w.attach'
        assert module.program is module.compiled.program
        assert purchase.program.model.pipelines[1].steps[2].compensate == 'c.delete-a'
    finally:
        sys.modules.pop(module.__name__)


def test_compile_can_omit_state_graph_without_inventing_business_states():
    assert purchase.compiled.graphs == ()
    assert purchase.PurchaseAttachment.upload.pipeline is purchase.upload_quotes
    assert purchase.save_quote_a.reads[0] is purchase.application_id
    assert registry.handlers[purchase.save_quote_a.id].__name__ == 'put_a'


def test_copied_compensation_identity_is_rejected():
    value, action, pipeline, flow, _ = symbolic_example()
    copied = replace(action.compensate)
    second = replace(action, id='s.second', compensate=copied)
    flow.save = replace(flow.save, pipeline=replace(pipeline, steps=(action, second)))
    with pytest.raises(ContractError, match='different objects share'):
        compile_workflows(flow, artifacts=(value,))


def test_console_script_can_import_application_from_working_directory(tmp_path):
    script = tmp_path / 'console.py'
    script.write_text('from myworkflow.cli import main\nraise SystemExit(main())\n')
    result = subprocess.run([sys.executable, str(script), 'build', '--config', 'examples.apps.purchase.build',
        '--target', 'kestra', '--workflow', 'w.attach', '--output', str(tmp_path / 'output')],
        cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / 'output/manifest.yaml').exists()
