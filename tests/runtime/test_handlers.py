"""The ingress/response boundary composes a pipeline without duplicating its declarations."""
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from myworkflow import Artifact, HandlerContract, Role, annotate
from myworkflow.build import BuildConfig, compile_outputs
from myworkflow.compiler.declarations import WorkflowDeclaration, bind, compile_workflows, trigger
from myworkflow.compiler.pipelines import PipelineDeclaration, StepDeclaration
from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.results import PipelineResult
from myworkflow.runtime import Context, Engine, Handler, Principal
from myworkflow.runtime.registry import Registry


@pytest.fixture
def boundary():
    value = Artifact('a.value', '入力', 'value')
    output = Artifact('a.output', '成果物', 'output')
    operator = Role('role.operator', '窓口担当者', '操作者')
    calls, journal = [], []

    @annotate(StepDeclaration('s.save', '保存', '入力を大文字にする。', reads=(value,), writes=(output,)))
    def save(ctx: Context) -> None:
        calls.append((ctx.actor, ctx.values['value']))
        ctx.values['output'] = ctx.values['value'].upper()

    pipeline = PipelineDeclaration('p.save', '保存', (value,), (output,), (save,))

    @annotate(WorkflowDeclaration('w.save', '受付業務'))
    class Flow:
        api = trigger('t.api', '画面から保存', operator, ((value, 'payload'),))
        job = trigger('t.job', 'ジョブから保存', operator, ((value, 'job_value'),))
        save = bind('b.save', pipeline, (api, job), (('system', operator),))

    compiled = compile_workflows(Flow, artifacts=(value, output))
    registry = Registry()
    registry.register(save)
    store = SimpleNamespace(begin=lambda run_id: journal.append(('begin', run_id)),
                            record=lambda *args: journal.append(('record', *args)))
    engine = Engine(compiled.program, registry, None, store=store)
    return SimpleNamespace(engine=engine, compiled=compiled, registry=registry, store=store,
                           calls=calls, journal=journal, principal=Principal('alice', frozenset({operator.id})))


def test_two_ingresses_share_a_pipeline_and_adapt_results_independently(boundary):
    api = boundary.engine.handler('b.save', 't.api')
    job = boundary.engine.handler('b.save', 't.job')
    assert api.contract.pipeline is job.contract.pipeline
    assert api.contract.request is api.contract.pipeline.inputs
    assert api.contract.response is PipelineResult
    assert api.handle({'payload': 'screen'}, boundary.principal, run_id='api') == {'code': 0, 'messages': []}
    assert job.handle({'job_value': 'worker'}, boundary.principal, run_id='job', respond=lambda result: result.code) == 0
    assert boundary.calls == [('alice', 'screen'), ('alice', 'worker')]
    assert len([entry for entry in boundary.journal if entry[0] == 'begin']) == 2


@pytest.mark.parametrize(('payload', 'roles'), [
    ({'payload': 'value'}, frozenset()),
    ({}, frozenset({'role.operator'})),
    ({'payload': 1}, frozenset({'role.operator'})),
    ({'payload': 'value', 'extra': 'field'}, frozenset({'role.operator'})),
])
def test_invalid_ingress_fails_before_pipeline_execution(boundary, payload, roles):
    handler = boundary.engine.handler('b.save', 't.api')
    response = handler.handle(payload, Principal('alice', roles), run_id='bad',
                              respond=lambda result: (result.to_dict(), 200 if result.ok else 400))
    assert response[0]['code'] == 1
    assert response[1] == 400
    assert not boundary.calls
    assert not boundary.journal


def test_no_reply_suppresses_external_response_but_preserves_internal_result(boundary):
    from myworkflow.compiler.program import Program
    catalog = boundary.compiled.catalog
    program = Program.from_catalog(replace(catalog, pipelines=(replace(catalog.pipelines[0], reply=False),)))
    engine = Engine(program, boundary.registry, None, store=boundary.store)
    handler = engine.handler('b.save', 't.api')
    assert handler.contract.response is None
    def forbidden(result):
        raise AssertionError('No response adapter should run for a no-reply contract')
    assert handler.handle({'payload': 'background'}, boundary.principal, run_id='background', respond=forbidden) is None
    assert handler.invoke({'payload': 'internal'}, boundary.principal, run_id='internal').ok
    assert boundary.calls == [('alice', 'background'), ('alice', 'internal')]


def test_handler_rejects_unrelated_or_copied_declarations(boundary):
    contract = boundary.compiled.program.handler('b.save', 't.api')
    with pytest.raises(ContractError, match='declared triggers'):
        replace(contract, trigger=replace(contract.trigger))
    with pytest.raises(ContractError, match='binding pipeline'):
        replace(contract, pipeline=replace(contract.pipeline, id='p.other'))
    copied = replace(contract, pipeline=replace(contract.pipeline))
    with pytest.raises(ContractError, match='belong to its program'):
        Handler(boundary.compiled.program, copied, boundary.engine._run_or_raise)


def test_build_exports_the_same_handler_contract_used_for_execution(boundary):
    ir = json.loads(compile_outputs(BuildConfig(boundary.compiled, boundary.registry), target='temporal')['ir.json'])
    contracts = [boundary.compiled.program.handler('b.save', trigger).to_dict() for trigger in ('t.api', 't.job')]
    assert ir['handlers'] == contracts
    assert contracts[0]['request'] == {'artifacts': ['a.value'], 'mapping': {'a.value': 'payload'}, 'role': 'role.operator'}
    assert contracts[0]['response'] == 'PipelineResult'
    assert contracts[0]['produces'] == ['a.output']
