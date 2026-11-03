"""One metadata protocol supports direct assignment, decorators and custom outputs."""
from dataclasses import dataclass, replace
import inspect
import json
from types import SimpleNamespace

import pytest

from myworkflow import Artifact, Role, annotate, declaration
from myworkflow.build import BuildConfig, compile_outputs
from myworkflow.compiler.declarations import WorkflowDeclaration, bind, compile_workflows, state, transition, trigger
from myworkflow.compiler.pipelines import StepDeclaration, PipelineDeclaration
from myworkflow.compiler.program import Program
from myworkflow.contracts.errors import ContractError
from myworkflow.generation.business import business_to_spec, export_business
from myworkflow.runtime import Context, Engine, Principal
from myworkflow.runtime.registry import Registry


def annotated_flow(extensions=None):
    events = []
    role = Role('role.operator', '操作担当者', '操作者', extensions={'organization': '窓口'})
    value = Artifact('a.value', '入力値', 'value', extensions={'ui': {'widget': 'text'}})
    raw = extensions if extensions is not None else {'ui': {'label': '保存', 'tags': ['customer']}}

    @annotate(StepDeclaration('s.save', reads=(value,), writes=(value,), extensions=raw))
    def save(ctx: Context) -> None:
        """入力値を大文字にして保持する。"""
        events.append(ctx.values['value'])
        ctx.values['value'] = ctx.values['value'].upper()

    @annotate(PipelineDeclaration('p.save', '保存', (value,), (value,), (save,), extensions={'app': 'sample'}))
    def pipeline(unrelated=None):
        raise AssertionError('Pipeline discovery must not call the annotated function')

    pending = state('state.pending', '処理前', initial=True, extensions={'ui': {'color': 'gray'}})
    done = state('state.done', '処理後')
    event = trigger('t.save', '保存操作', role, ((value, 'input'),), extensions={'transport': 'http'})
    placement = bind('b.save', pipeline, (event,), (('system', role),), extensions={'screen': 'entry'})
    finish = transition('tr.save', '保存', pending, done, placement, event, extensions={'audit': True})

    def flow():
        raise AssertionError('Workflow discovery must not execute the annotated function')

    # Direct assignment and the decorator share the exact same metadata protocol.
    flow.__myworkflow__ = WorkflowDeclaration('w.save', '入力受付', (pending, done, placement, finish),
                                              extensions={'customer': {'department': '営業'}})
    compiled = compile_workflows(flow, artifacts=(value,))
    registry = Registry()
    registry.register(save)
    return compiled, registry, SimpleNamespace(save=save, pipeline=pipeline, flow=flow, raw=raw, events=events)


def test_protocol_keeps_callable_identity_and_does_not_require_an_execution_signature():
    @dataclass
    class CustomSpec:
        id: str
        purpose: str
    def original(first, *, second=1):
        return first + second
    signature = inspect.signature(original)
    spec = CustomSpec('custom.call', '独自用途')
    assert annotate(spec)(original) is original
    assert declaration(original) is spec
    assert inspect.signature(original) == signature
    assert original(2, second=3) == 5
    with pytest.raises(ContractError, match='already annotated'):
        annotate(spec)(original)


def test_static_compilation_and_runtime_use_the_same_function_declaration():
    compiled, registry, refs = annotated_flow()
    step = compiled.program.steps['s.save']
    assert step.name == 'save'
    assert step.summary == '入力値を大文字にして保持する。'
    assert compiled.workflow(refs.flow) is compiled.catalog.workflows[0]
    assert registry.handlers['s.save'] is refs.save
    journal = SimpleNamespace(begin=lambda identity: None, record=lambda *args: None)
    runner = Engine(compiled.program, registry, None, store=journal)
    assert runner.invoke('b.save', 't.save', {'input': 'hello'}, Principal('alice', frozenset({'role.operator'})), run_id='one').ok
    assert refs.events == ['hello']
    assert declaration(refs.pipeline).id == 'p.save'


def test_extensions_survive_compilation_specs_ir_and_business_roundtrip():
    compiled, registry, refs = annotated_flow()
    program = compiled.program
    refs.raw['ui']['label'] = '変更しても元の宣言へ影響しない'
    assert program.steps['s.save'].extensions['ui']['label'] == '保存'
    with pytest.raises(TypeError):
        program.steps['s.save'].extensions['ui']['label'] = '変更'
    output = export_business(program)
    restored = Program(business_to_spec(output))
    assert export_business(restored) == output
    assert export_business(Program(program.spec)) == output
    ir = json.loads(compile_outputs(BuildConfig(compiled, registry), target='temporal')['ir.json'])
    assert ir['business'] == output
    assert ir['state_graphs'][0]['states'][0]['extensions']['ui']['color'] == 'gray'
    assert ir['state_graphs'][0]['transitions'][0]['extensions'] == {'audit': True}
    assert output['roles']['role.operator']['extensions']['organization'] == '窓口'
    assert output['artifacts']['a.value']['extensions']['ui']['widget'] == 'text'
    assert output['pipelines']['p.save']['extensions'] == {'app': 'sample'}
    assert output['bindings']['b.save']['extensions'] == {'screen': 'entry'}
    assert output['triggers']['t.save']['extensions'] == {'transport': 'http'}
    assert output['workflows']['w.save']['extensions']['customer']['department'] == '営業'


def test_opaque_extensions_need_an_explicit_encoder_and_can_drive_custom_documents():
    token = object()
    compiled, registry, refs = annotated_flow({'custom': token})
    assert compiled.program.steps['s.save'].extensions['custom'] is token
    with pytest.raises(ContractError, match='extension_encoder'):
        export_business(compiled.program)
    with pytest.raises(ContractError, match='extension_encoder'):
        _ = compiled.program.spec
    def document(program, graphs, implementations):
        assert program.steps['s.save'].extensions['custom'] is token
        assert graphs and implementations is registry
        return '# 顧客向け独自帳票\n'
    config = BuildConfig(compiled, registry, document_renderer=document,
                         extension_encoder=lambda value: 'external-reference' if value is token else value)
    outputs = compile_outputs(config, target='temporal')
    assert outputs['requirements.md'] == '# 顧客向け独自帳票\n'
    assert json.loads(outputs['ir.json'])['business']['steps']['s.save']['extensions'] == {'custom': 'external-reference'}
    with pytest.raises(ValueError, match='must return a string'):
        compile_outputs(replace(config, document_renderer=lambda *args: None), target='temporal')


@pytest.mark.parametrize('extensions', [[], {1: 'not a string key'}])
def test_invalid_extension_containers_are_rejected(extensions):
    with pytest.raises(ContractError):
        StepDeclaration('s.bad', extensions=extensions)


def test_value_definitions_and_catalog_extensions_survive_explicit_registry_loading():
    from examples.apps.purchase.value_objects import application_id_type
    definition = replace(application_id_type, extensions={'customer': {'meaning': '購買番号'}})
    value = Artifact('a.id', '識別子', 'identity', value_object=definition)
    from myworkflow import ContractCatalog
    catalog = ContractCatalog((value,), (), (), value_objects=(definition,), extensions={'catalog': {'version': 1}})
    program = Program.from_catalog(catalog)
    output = export_business(program)
    assert output['value_objects'][definition.id]['extensions']['customer']['meaning'] == '購買番号'
    assert output['extensions']['catalog']['version'] == 1
    restored = Program(business_to_spec(output), value_objects=(definition,))
    assert export_business(restored) == output


def test_cyclic_extension_containers_fail_at_declaration_time():
    cycle = {}
    cycle['self'] = cycle
    with pytest.raises(ContractError, match='acyclic'):
        StepDeclaration('s.cycle', extensions=cycle)


def test_plain_declarations_do_not_use_the_dataclass_signature_as_a_business_summary():
    compiled, registry, refs = annotated_flow()
    refs.pipeline.__myworkflow__ = replace(declaration(refs.pipeline), steps=(StepDeclaration('s.undocumented', '説明なし'),))
    with pytest.raises(ContractError, match='business summary'):
        compile_workflows(refs.flow, artifacts=compiled.catalog.artifacts)


@pytest.mark.parametrize('encoder', [lambda value: {1: 'invalid key'}, lambda value: {'self': value}])
def test_custom_encoders_cannot_silently_change_keys_or_recurse_forever(encoder):
    compiled, registry, refs = annotated_flow({'custom': object()})
    with pytest.raises(ContractError):
        export_business(compiled.program, extension_encoder=encoder)


def test_standard_dataclass_conversion_still_supports_extension_metadata():
    from dataclasses import asdict
    action = StepDeclaration('s.export', extensions={'ui': {'tags': ['customer']}})
    exported = json.loads(json.dumps(asdict(action)))
    assert exported['extensions'] == {'ui': {'tags': ['customer']}}
    with pytest.raises(TypeError):
        action.extensions['ui'].update({'label': '変更'})


@pytest.mark.parametrize('module_name', [
    'examples.apps.purchase.handlers',
    'examples.apps.tickets.application',
    'examples.feature_demos.approval_values.application',
    'examples.feature_demos.prepared_approval.application',
])
def test_sample_registries_use_their_function_annotations(module_name):
    from importlib import import_module
    module = import_module(module_name)
    assert module.registry.handlers
    for identity, handler in module.registry.handlers.items():
        assert declaration(handler) is not handler
        assert declaration(handler).id == identity
