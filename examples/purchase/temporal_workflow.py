"""Detailed orchestration is handwritten; pipeline contracts remain code-owned."""
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from examples.purchase.contract import SPEC

APPROVAL = SPEC['workflows'][0]
EXECUTION = SPEC['workflows'][2]
START = APPROVAL['bindings'][2]


async def pipeline(binding, trigger, payload, actor, roles):
    return await workflow.execute_activity(
        'myworkflow.pipeline',
        {'binding': binding, 'trigger': trigger, 'payload': payload, 'actor': actor, 'roles': roles},
        start_to_close_timeout=timedelta(seconds=10), retry_policy=RetryPolicy(maximum_attempts=1),
    )


@workflow.defn(name=EXECUTION['id'])
class ConfirmPurchase:
    @workflow.run
    async def run(self, request: dict) -> dict:
        b = EXECUTION['bindings'][0]
        await pipeline(b['id'], b['triggers'][0]['id'], {'id': request['application_id']}, 'system', ['role.system'])
        return {'application_id': request['application_id'], 'status': 'confirmed'}


@workflow.defn(name=APPROVAL['id'])
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
        await pipeline('b.submit', 't.submit', {'id': identity, 'vendor': request['vendor'], 'amount': request['amount']},
                       request['applicant'], ['role.requester'])
        await pipeline('b.upload', 't.upload', {'id': identity, 'file_a': request['quote_a'], 'file_b': request['quote_b']},
                       request['applicant'], ['role.requester'])
        self.phase = 'waiting-approval'
        await workflow.wait_condition(lambda: self.decision is not None)
        decision = self.decision
        result = await pipeline('b.approve', 't.approve', {'id': identity, 'decision': decision['approved']},
                                decision['actor'], decision['roles'])
        if result['status'] == 'rejected':
            self.phase = 'rejected'
            return {'application_id': identity, 'status': 'rejected'}
        self.phase = 'waiting-schedule'
        await workflow.sleep(timedelta(seconds=request.get('delay_seconds', 0)))
        handoff = await pipeline(START['id'], START['triggers'][0]['id'], {'id': identity}, 'system', ['role.system'])
        self.phase = 'confirming'
        result = await workflow.execute_child_workflow(
            START['next_workflow'], handoff, id=f'{workflow.info().workflow_id}/confirm',
        )
        self.phase = 'completed'
        return result
