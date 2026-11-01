"""Activity result serialization and error classification, using the real SDK harness."""
import pytest
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment

from examples.apps.purchase import interfaces
from examples.apps.purchase.contract import program
from examples.apps.purchase.handlers import registry
from examples.apps.purchase.services import Services
from myworkflow.contracts.errors import BusinessError, ExecutionFailed
from myworkflow.executable import Engine, Principal, Program
from myworkflow.adapters.temporal import PipelineActivity


@pytest.fixture
def activity(tmp_path):
    return PipelineActivity(Engine(program, registry, Services(tmp_path / 'app.db'), interfaces))


def submit(engine):
    engine.invoke_or_raise('b.submit', 't.submit', {'id': 'x', 'vendor': 'V', 'amount': 100},
                           Principal('alice', frozenset({'role.requester'})), run_id='seed')


@pytest.mark.asyncio
async def test_success_contains_completion_only(activity):
    result = await ActivityEnvironment().run(activity.invoke, {
        'binding': 'b.submit', 'trigger': 't.submit', 'payload': {'id': 'x', 'vendor': 'V', 'amount': 100},
        'actor': 'alice', 'roles': ['role.requester'],
    })
    assert result == {'code': 0, 'messages': [{'level': 'info', 'text': '申請を受け付けました'}]}
    assert activity.engine.services.application('x')['status'] == 'waiting-approval'


@pytest.mark.asyncio
async def test_business_rejection_returns_code_without_activity_failure(activity):
    submit(activity.engine)
    activity.engine.invoke_or_raise('b.approve', 't.approve', {'id': 'x', 'decision': True},
                                    Principal('bob', frozenset({'role.approver'})), run_id='approve')
    result = await ActivityEnvironment().run(activity.invoke, {
        'binding': 'b.confirm', 'trigger': 't.confirm', 'payload': {'id': 'x'},
        'actor': 'system', 'roles': ['role.system'],
    })
    assert result['code'] == 10
    assert result['messages'][0]['level'] == 'warning'
    assert activity.engine.services.application('x')['status'] == 'approved'


@pytest.mark.asyncio
async def test_contract_error_is_an_activity_failure_with_completion_details(activity):
    with pytest.raises(ApplicationError) as caught:
        await ActivityEnvironment().run(activity.invoke, {
            'binding': 'b.submit', 'trigger': 't.submit', 'payload': {'id': 'x', 'vendor': 'V', 'amount': 'bad'},
            'actor': 'alice', 'roles': ['role.requester'],
        })
    assert caught.value.type == 'ContractError'
    assert caught.value.details[0]['result']['code'] == 1
    assert caught.value.non_retryable  # Whole-pipeline replay is intentionally still disabled.


@pytest.mark.asyncio
async def test_retry_exhaustion_remains_an_activity_failure(activity):
    submit(activity.engine)
    activity.engine.services.failures['put-B'] = ['before', 'before']
    with pytest.raises(ApplicationError) as caught:
        await ActivityEnvironment().run(activity.invoke, {
            'binding': 'b.upload', 'trigger': 't.upload', 'payload': {'id': 'x', 'file_a': 'A', 'file_b': 'B'},
            'actor': 'alice', 'roles': ['role.requester'],
        })
    assert caught.value.type == 'RetryExhausted'
    assert caught.value.details[0]['result']['code'] == 1
    with activity.engine.services.connect() as db:
        assert db.execute('SELECT count(*) FROM objects').fetchone()[0] == 0


@pytest.mark.asyncio
async def test_failed_compensation_cannot_be_returned_as_ordinary_business_rejection():
    class FailedEngine:
        def invoke_or_raise(self, *args, **kwargs):
            raise ExecutionFailed('step', BusinessError(42, '拒否', level='warning'), [('undo', 'failed')])
    with pytest.raises(ApplicationError) as caught:
        await ActivityEnvironment().run(PipelineActivity(FailedEngine()).invoke, {
            'binding': 'b', 'trigger': 't', 'payload': {}, 'actor': 'a', 'roles': [],
        })
    result = caught.value.details[0]['result']
    assert result['code'] == 1
    assert result['messages'][-1]['level'] == 'critical'


@pytest.mark.asyncio
async def test_adapter_uses_failure_kind_rather_than_code_one_alone():
    class RejectedEngine:
        def invoke_or_raise(self, *args, **kwargs):
            raise BusinessError(1, '業務上の拒否', level='warning')
    result = await ActivityEnvironment().run(PipelineActivity(RejectedEngine()).invoke, {
        'binding': 'b', 'trigger': 't', 'payload': {}, 'actor': 'a', 'roles': [],
    })
    assert result == {'code': 1, 'messages': [{'level': 'warning', 'text': '業務上の拒否'}]}
