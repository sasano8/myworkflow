"""Dedicated syntax builds the same declarations without introducing execution behavior."""
import inspect

import pytest

from myworkflow import Artifact, Role, declaration, pipeline, step, workflow
from myworkflow.compiler.declarations import WorkflowDeclaration, bind, compile_workflows, trigger
from myworkflow.compiler.pipelines import Operation, PipelineDeclaration, StepDeclaration
from myworkflow.contracts.errors import ContractError
from myworkflow.generation.business import export_business
from myworkflow.runtime import Context, Engine, Principal
from myworkflow.runtime.registry import Registry


def test_step_preserves_identity_signature_and_all_standard_options():
    value = Artifact('a.value', '値', 'value')
    flag = Artifact('a.flag', '条件', 'flag', 'bool')
    undo = Operation('c.undo')
    extensions = {'customer': {'department': '購買'}}
    def original(first: int, *, second: int = 1) -> int:
        return first + second
    before = inspect.signature(original)
    decorator = step(id='s.test', name='処理', summary='処理する。', reads=(value,), writes=(value,),
                     uses=((value, '保持'),), when=(flag, True), compensate=undo, attempts=2,
                     actor='operator', extensions=extensions)
    result = decorator(original)
    assert result is original
    assert inspect.signature(result) == before
    assert result(2, second=3) == 5
    assert declaration(result) == StepDeclaration('s.test', '処理', '処理する。', (value,), (value,),
                                                 ((value, '保持'),), (flag, True), undo, 2, 'operator', extensions=extensions)
    with pytest.raises(ContractError, match='already annotated'):
        decorator(result)


def test_syntax_compiles_static_references_and_executes_only_steps():
    value = Artifact('a.input', '入力', 'value')
    role = Role('role.operator', '担当者', '操作者')
    seen = []

    @step(id='s.record', reads=(value,), extensions={'ui': {'label': '記録'}})
    def record(ctx: Context) -> None:
        """入力を記録する。"""
        seen.append(ctx.values['value'])

    @pipeline(id='p.record', inputs=(value,), steps=(record,), reply=False, extensions={'api': 'background'})
    def record_pipeline():
        raise AssertionError('Pipeline body is not an execution plan')

    event = trigger('t.record', '記録操作', role, ((value, 'input'),))
    placement = bind('b.record', record_pipeline, (event,), (('system', role),))

    @workflow(id='w.record', members=(placement,), extensions={'customer': 'example'})
    def Recording():
        raise AssertionError('Workflow body must not run during compilation')

    assert isinstance(declaration(record_pipeline), PipelineDeclaration)
    assert declaration(record_pipeline).name == 'record_pipeline'
    assert isinstance(declaration(Recording), WorkflowDeclaration)
    assert declaration(Recording).name == 'Recording'
    compiled = compile_workflows(Recording, artifacts=(value,))
    assert not seen
    assert compiled.program.steps['s.record'].summary == '入力を記録する。'
    assert compiled.program.steps['s.record'].name == 'record'
    assert export_business(compiled.program)['steps']['s.record']['extensions']['ui']['label'] == '記録'
    registry = Registry()
    registry.register(record)
    class Journal:
        def begin(self, identity): pass
        def record(self, *args): pass
    engine = Engine(compiled.program, registry, None, store=Journal())
    assert engine.handler(placement, event).handle({'input': 'hello'}, Principal('alice', frozenset({role.id})), run_id='one') is None
    assert seen == ['hello']


@pytest.mark.parametrize('decorate', [
    lambda: step(id='s.bad', extensions=[]),
    lambda: pipeline(id='p.bad', extensions=[])(lambda: None),
    lambda: workflow(id='w.bad', extensions=[])(lambda: None),
])
def test_syntax_uses_shared_extension_validation(decorate):
    with pytest.raises(ContractError, match='mapping'):
        decorate()


def test_workflow_class_keeps_named_members_and_constructor_identity():
    class Definition:
        pass
    assert workflow(id='w.empty', name='空の業務')(Definition) is Definition
    assert compile_workflows(Definition).workflow(Definition).name == '空の業務'
