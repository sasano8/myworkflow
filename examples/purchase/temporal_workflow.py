"""Detailed orchestration is handwritten; pipeline contracts remain code-owned."""
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from examples.purchase.contract import SPEC
    from myworkflow.program import Program

PROGRAM = Program(SPEC)
APPROVAL_ID = 'w.approval'
START = PROGRAM.binding('b.dispatch')
TARGET = PROGRAM.next_binding(START.id, 'b.confirm')
EXECUTION_ID = START.next_workflow_id


async def pipeline(binding, trigger, payload, actor, roles):
    result = await workflow.execute_activity(
        'myworkflow.pipeline',
        {'binding': binding, 'trigger': trigger, 'payload': PROGRAM.payload(binding, trigger, payload), 'actor': actor, 'roles': roles},
        start_to_close_timeout=timedelta(seconds=10), retry_policy=RetryPolicy(maximum_attempts=1),
    )
    if result['code'] != 0:
        raise ApplicationError('Pipeline rejected', result, type='BusinessRejected', non_retryable=True)
    return result


@workflow.defn(name=EXECUTION_ID)
class ConfirmPurchase:
    @workflow.run
    async def run(self, request: dict) -> dict:
        await pipeline(TARGET.id, 't.confirm', {'application_id': request['application_id']}, 'system', ['role.system'])
        return {'application_id': request['application_id'], 'status': 'confirmed'}


@workflow.defn(name=APPROVAL_ID)
class ApprovePurchase:
    def __init__(self):
        self.decision = None
        self.phase = 'submitting'

    @workflow.signal
    def decide(self, decision: dict):
        if self.decision is None:
            self.decision = decision

    @workflow.query
    def state(self) -> str:
        return self.phase

    @workflow.run
    async def run(self, request: dict) -> dict:
        identity = request['application_id']
        await pipeline('b.submit', 't.submit', {'application_id': identity, 'vendor': request['vendor'], 'amount': request['amount']},
                       request['applicant'], ['role.requester'])
        await pipeline('b.upload', 't.upload', {'application_id': identity, 'quote_a': request['quote_a'], 'quote_b': request['quote_b']},
                       request['applicant'], ['role.requester'])
        self.phase = 'waiting-approval'
        await workflow.wait_condition(lambda: self.decision is not None)
        decision = self.decision
        result = await pipeline('b.approve', 't.approve', {'application_id': identity, 'decision': decision['approved']},
                                decision['actor'], decision['roles'])
        if not decision['approved']:
            self.phase = 'rejected'
            return {'application_id': identity, 'status': 'rejected'}
        self.phase = 'waiting-schedule'
        await workflow.sleep(timedelta(seconds=request.get('delay_seconds', 0)))
        await pipeline(START.id, 't.timer', {'application_id': identity}, 'system', ['role.system'])
        self.phase = 'confirming'
        result = await workflow.execute_child_workflow(
            START.next_workflow_id, {'application_id': identity}, id=f'{workflow.info().workflow_id}/confirm',
        )
        self.phase = 'completed'
        return result
