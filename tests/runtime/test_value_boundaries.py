"""Value-object runtime behavior."""
from dataclasses import replace
import pytest
from pydantic import BaseModel
from examples.feature_demos.approval_values import application as sample
from examples.feature_demos.approval_values.value_objects import ApplicationId, approval_application, delivery_period
from myworkflow import Trigger, Artifact, ValueObject
from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.storage.artifacts import ArtifactWrite
from myworkflow.contracts.errors import ContractError, ExecutionFailed
from myworkflow.executable import Context, Engine, Principal, Registry
from myworkflow.compiler.program import Program
from myworkflow.runtime.changes import Changes

def test_mutable_models_and_unregistered_record_types_are_rejected(tmp_path):
    class Mutable(BaseModel):
        value: int
    with pytest.raises(ContractError, match='frozen'):
        ValueObject('vo.mutable', '変更可能', Mutable).check()
    provider = TemporaryArtifactCoordinator(tmp_path)
    with pytest.raises(ContractError, match='declared ValueObject'):
        Changes(provider).read('missing', value_object=approval_application)



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
    binding = Binding('b.process', pipeline.id, (Trigger('t.process', '入力', ((data.id, 'data'),), actor_role_id=role.id),), role_mapping=(('system', role.id),))
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



@pytest.mark.parametrize('vendor, amount', [('V', 0), ('V', -1), ('', 1), ('   ', 1)])
def test_purchase_value_constraints_reject_before_storage(tmp_path, vendor, amount):
    from examples.apps.purchase import contract, interfaces
    from examples.apps.purchase.handlers import registry
    from examples.apps.purchase.services import Services
    services = Services(tmp_path / 'purchase.db')
    runner = Engine(contract.program, registry, services, interfaces)
    result = runner.invoke(contract.PurchaseApproval.submit, contract.PurchaseApproval.submission,
                           {'id': 'x', 'vendor': vendor, 'amount': amount},
                           Principal('alice', frozenset({contract.requester.id})), run_id='invalid')
    assert not result.ok
    with services.connect() as database:
        assert database.execute('SELECT COUNT(*) FROM applications').fetchone()[0] == 0
