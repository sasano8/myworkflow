"""Data contracts, independent documents and boundary validation."""
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
from types import ModuleType
from typing import get_type_hints

import pytest
from pydantic import BaseModel, Field, ValidationError, model_validator

from examples import guarded_approval as sample
from examples.approval_values import (ApplicationId, ApprovalApplication, DeliveryPeriod, PurchaseAmount,
                                     application_identifier, approval_application, delivery_period, purchase_amount)
from examples.approval_values_build import BUILD
from myworkflow import Artifact, ValueModel, ValueObject
from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.artifact_jobs import ArtifactWrite
from myworkflow.build import build, compile_outputs
from myworkflow.codegen import interfaces_source
from myworkflow.declarations import compile_workflows
from myworkflow.errors import ContractError, ExecutionFailed
from myworkflow.executable import Context, Engine, Principal, Registry
from myworkflow.program import Program
from myworkflow.quality.business import business_to_spec, export_business
from myworkflow.quality.interfaces import check_interfaces
from myworkflow.runtime.changes import Changes
from myworkflow.value_objects import data_definitions_source, render_data_definitions

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('value', [0, -1, 1.5, True, '100', float('nan')])
def test_money_rejects_invalid_or_ambiguous_values(value):
    with pytest.raises(ContractError, match='invalid value'):
        purchase_amount.normalize(value)


def test_models_are_frozen_and_validation_cannot_be_bypassed_with_construct():
    amount = PurchaseAmount(100)
    assert purchase_amount.normalize(amount) == 100
    with pytest.raises(ValidationError):
        amount.root = 200
    with pytest.raises(ContractError):
        purchase_amount.normalize(PurchaseAmount.model_construct(root=-100))
    assert approval_application.normalize({'owner': 'alice', 'amount': 100, 'status': 'waiting'})['approved_by'] is None
    with pytest.raises(ContractError):
        approval_application.normalize({'owner': 'alice', 'amount': 100, 'status': 'waiting', 'unknown': True})


def test_cross_field_rule_runs_but_is_not_claimed_as_json_schema_constraint():
    assert delivery_period.normalize(DeliveryPeriod(starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 1))) == {
        'starts_on': '2026-01-01', 'ends_on': '2026-01-01'}
    with pytest.raises(ContractError, match='終了日'):
        delivery_period.normalize({'starts_on': '2026-11-30', 'ends_on': '2026-11-01'})
    definition = delivery_period.definition()
    assert definition['rules'] == ['終了日は開始日以降とする。同日も許可する。']
    assert definition['validators'] == [{'name': 'dates_in_order', 'kind': 'model_validators', 'fields': []}]
    assert definition['schema']['properties']['starts_on']['format'] == 'date'


def test_independent_data_documents_match_reviewed_samples_and_business_links():
    catalog = sample.compiled.catalog
    markdown = render_data_definitions(catalog)
    assert markdown == (ROOT / 'examples/approval-values/data-definitions.md').read_text()
    assert data_definitions_source(catalog) == (ROOT / 'examples/approval-values/data-definitions.json').read_text()
    assert 'JSON Schemaだけでは全条件を表せない' in markdown
    assert 'exclusiveMinimum' in markdown
    assert 'data-definitions.md#vo.application_id' in sample.compiled.program.documentation()
    assert 'exclusiveMinimum' not in sample.compiled.program.documentation()
    assert compile_outputs(BUILD, target='temporal')['requirements.md'] == (ROOT / 'examples/approval-values/requirements.md').read_text()


def test_build_includes_separate_data_files_and_detects_constraint_drift(tmp_path):
    outputs = build(BUILD, tmp_path, target='temporal')
    assert outputs['data-definitions.md'] == render_data_definitions(sample.compiled.catalog)
    assert json.loads(outputs['build.json'])['files']['data-definitions.json']
    build(BUILD, tmp_path, target='temporal', check=True)
    target = tmp_path / 'data-definitions.json'
    target.write_text('{}')
    with pytest.raises(ValueError, match='stale'):
        build(BUILD, tmp_path, target='temporal', check=True)
    assert target.read_text() == '{}'


def test_registry_identity_and_primitive_shape_are_checked():
    with pytest.raises(ContractError, match='different objects'):
        compile_workflows(sample.Approval, artifacts=(sample.application_id,),
                          value_objects=(replace(application_identifier),))
    catalog = sample.compiled.catalog
    with pytest.raises(ContractError, match='JSON type'):
        Program.from_catalog(replace(catalog, artifacts=(replace(sample.application_id, type='int'),)))
    with pytest.raises(ContractError, match='unique'):
        Program.from_catalog(replace(catalog, value_objects=(*catalog.value_objects, application_identifier)))


def test_mutable_models_and_unregistered_record_types_are_rejected(tmp_path):
    class Mutable(BaseModel):
        value: int
    with pytest.raises(ContractError, match='frozen'):
        ValueObject('vo.mutable', '変更可能', Mutable).check()
    provider = TemporaryArtifactCoordinator(tmp_path)
    with pytest.raises(ContractError, match='declared ValueObject'):
        Changes(provider).read('missing', value_object=approval_application)


def test_export_roundtrip_requires_explicit_models_and_never_imports_document_paths():
    program = sample.compiled.program
    business = export_business(program)
    spec = business_to_spec(business)
    with pytest.raises(ContractError, match='explicit Python'):
        Program(spec)
    rebuilt = Program(spec, value_objects=sample.compiled.catalog.value_objects)
    assert export_business(rebuilt) == business
    changed = json.loads(json.dumps(spec))
    changed['value_objects'][0]['schema']['pattern'] = 'different'
    with pytest.raises(ContractError, match='explicit Python'):
        Program(changed, value_objects=sample.compiled.catalog.value_objects)


def test_generated_request_references_the_original_model_class():
    module = ModuleType('generated_value_interfaces')
    exec(interfaces_source(sample.compiled.program), module.__dict__)
    assert get_type_hints(module.PGuarded_ApproveRequest)['application_id'] is ApplicationId
    assert check_interfaces(export_business(sample.compiled.program), module)['passed']
    Engine(sample.compiled.program, sample.registry, None, module,
           store=type('Journal', (), {'begin': lambda *a: None, 'record': lambda *a: None})())


def test_invalid_request_fails_before_handler_and_valid_request_accepts_model(tmp_path):
    provider = TemporaryArtifactCoordinator(tmp_path)
    sample.seed(provider)
    runner = sample.engine(provider, tmp_path / 'runs.db')
    actor = Principal('bob', frozenset({sample.reviewer.id}))
    result = runner.invoke(sample.Approval.execute, sample.Approval.requested, {'id': '../bad'}, actor, run_id='invalid')
    assert not result.ok
    assert provider.status('invalid') is None
    result = runner.invoke(sample.Approval.execute, sample.Approval.requested, {'id': ApplicationId('example')}, actor, run_id='valid')
    assert result.ok


def test_invalid_changes_fail_before_prepare_and_preserve_version(tmp_path):
    provider = TemporaryArtifactCoordinator(tmp_path)
    sample.seed(provider)
    handlers = sample.registry.fork()
    def invalid(ctx: Context) -> None:
        sample.approve(ctx)
        ctx.changes.update(ctx.changes.subject, amount=-100)
    handlers.replace(sample.record_approval, invalid)
    runner = sample.engine(provider, tmp_path / 'runs.db', handlers=handlers)
    with pytest.raises(ExecutionFailed, match='invalid value'):
        runner.invoke_or_raise(sample.Approval.execute, sample.Approval.requested, {'id': 'example'},
                               Principal('bob', frozenset({sample.reviewer.id})), run_id='invalid')
    assert provider.status('invalid') is None
    assert provider.read('application:example').version == 1


def test_extra_typed_records_use_their_contract_and_cannot_change_type(tmp_path):
    provider = TemporaryArtifactCoordinator(tmp_path)
    provider.prepare('seed', (ArtifactWrite('period', {'starts_on': '2026-01-01', 'ends_on': '2026-12-01'}),))
    provider.commit('seed')
    changes = Changes(provider, value_objects=(delivery_period, approval_application))
    record = changes.read('period', value_object=delivery_period)
    with pytest.raises(ContractError, match='cannot be changed'):
        changes.read('period', value_object=approval_application)
    changes.update(record, ends_on='2025-01-01')
    with pytest.raises(ContractError, match='終了日'):
        changes._writes()


def typed_pipeline_program():
    from myworkflow import ContractCatalog, Pipeline, Role, Step, Binding, Workflow
    data = Artifact('a.data', '購買申請', 'data', 'dict', value_object=approval_application)
    step = Step('s.process', '処理', '内容を確認する', reads=(data.id,))
    pipeline = Pipeline('p.process', '処理', (data.id,), (), (step,))
    role = Role('role.user', '利用者', '利用者')
    binding = Binding('b.process', pipeline.id, '入力', ((data.id, 'data'),), actor_role_id=role.id,
                      role_mapping=(('system', role.id),), trigger_id='t.process')
    catalog = ContractCatalog((data,), (pipeline,), (Workflow('w.process', '処理', (binding,)),), (role,), (approval_application,))
    return Program.from_catalog(catalog)


def test_structured_input_defaults_and_undeclared_nested_mutation(tmp_path):
    from myworkflow.adapters.sqlite import SQLiteDatabase, SQLiteExecutionStore
    program = typed_pipeline_program()
    handlers = Registry()
    @handlers.implements('s.process')
    def process(ctx: Context) -> None:
        assert ctx.values['data']['approved_by'] is None
        ctx.values['data']['amount'] = -1
    runner = Engine(program, handlers, None, store=SQLiteExecutionStore(SQLiteDatabase(tmp_path / 'runs.db')))
    result = runner.invoke('b.process', 't.process', {'data': {'owner': 'alice', 'amount': 1, 'status': 'waiting'}},
                           Principal('bob', frozenset({'role.user'})), run_id='mutate')
    assert not result.ok
    assert 'undeclared context writes' in result.messages[-1].text



def test_nested_models_and_input_aliases_are_visible_in_data_definition():
    class Nested(DeliveryPeriod):
        pass
    class Envelope(ValueModel):
        period: Nested = Field(alias='deliveryWindow', description='納品受付期間。')
    definition = ValueObject('vo.envelope', '納品情報', Envelope)
    details = definition.definition()
    assert 'Nested' in details['schema']['$defs']
    assert details['input_aliases'] == {'period': 'deliveryWindow'}
    assert any(v.get('model', '').endswith('.Nested') for v in details['validators'])
    expected = {'period': {'starts_on': '2026-01-01', 'ends_on': '2026-02-01'}}
    assert definition.normalize({'deliveryWindow': expected['period']}) == expected
    assert definition.normalize(expected) == expected


@pytest.mark.parametrize('amount, success', [(0, False), (10, True)])
def test_declared_step_writes_are_validated_as_value_objects(tmp_path, amount, success):
    from myworkflow.adapters.sqlite import SQLiteDatabase, SQLiteExecutionStore
    program = typed_pipeline_program()
    original = program.model
    pipeline = original.pipelines[0]
    step = replace(pipeline.steps[0], writes=('a.data',))
    program = Program.from_catalog(replace(original, pipelines=(replace(pipeline, steps=(step,)),)))
    handlers = Registry()
    @handlers.implements('s.process')
    def process(ctx: Context) -> None:
        ctx.values['data'] = {'owner': 'alice', 'amount': amount, 'status': 'waiting'}
    runner = Engine(program, handlers, None, store=SQLiteExecutionStore(SQLiteDatabase(tmp_path / 'runs.db')))
    result = runner.invoke('b.process', 't.process', {'data': {'owner': 'alice', 'amount': 1, 'status': 'waiting'}},
                           Principal('bob', frozenset({'role.user'})), run_id='write')
    assert result.ok is success
    if not success:
        assert 'invalid value' in result.messages[-1].text



def test_interface_inspection_detects_schema_drift_even_with_same_python_name():
    from pydantic import create_model
    from typing import Annotated
    module = ModuleType('generated_value_interfaces')
    exec(interfaces_source(sample.compiled.program), module.__dict__)
    changed = create_model('ApplicationId', __base__=ApplicationId,
                           root=(Annotated[str, Field(pattern='^DIFFERENT$')], ...))
    changed.__module__ = ApplicationId.__module__
    changed.__qualname__ = ApplicationId.__qualname__
    module.PGuarded_ApproveRequest.__annotations__['application_id'] = changed
    report = check_interfaces(export_business(sample.compiled.program), module)
    assert not report['passed']
    assert report['errors'][0]['schema_errors'] == ['vo.application_id']



def test_purchase_owns_value_definitions_and_builds_frozen_documents():
    from examples.purchase import contract, value_objects
    from examples.purchase.build import BUILD as purchase_build
    assert contract.amount.value_object is value_objects.amount_type
    assert contract.vendor.value_object is value_objects.vendor_type
    assert contract.application_id.value_object is value_objects.application_id_type
    outputs = compile_outputs(purchase_build, target='temporal')
    for name in ('data-definitions.md', 'data-definitions.json'):
        assert outputs[name] == (ROOT / 'examples/purchase' / name).read_text()
    assert 'data-definitions.md#vo.purchase.amount' in contract.program.documentation()
    from myworkflow.acceptance.rendering import DocumentOptions, render_business
    options = DocumentOptions(data_definitions_link='../data-definitions.md')
    assert '../data-definitions.md#vo.purchase.amount' in render_business(contract.program, None, (), options=options)


@pytest.mark.parametrize('vendor, amount', [('V', 0), ('V', -1), ('', 1), ('   ', 1)])
def test_purchase_value_constraints_reject_before_storage(tmp_path, vendor, amount):
    from examples.purchase import contract, interfaces
    from examples.purchase.handlers import registry
    from examples.purchase.services import Services
    services = Services(tmp_path / 'purchase.db')
    runner = Engine(contract.program, registry, services, interfaces)
    result = runner.invoke(contract.PurchaseApproval.submit, contract.PurchaseApproval.submission,
                           {'id': 'x', 'vendor': vendor, 'amount': amount},
                           Principal('alice', frozenset({contract.requester.id})), run_id='invalid')
    assert not result.ok
    with services.connect() as database:
        assert database.execute('SELECT COUNT(*) FROM applications').fetchone()[0] == 0
