"""Detailed orchestration is handwritten; pipeline contracts remain code-owned."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from examples.apps.purchase import contract as c

PROGRAM = c.program
APPROVAL_ID = c.compiled.workflow(c.PurchaseApproval).id
START = PROGRAM.binding(c.PurchaseApproval.dispatch)
TARGET = PROGRAM.next_binding(START.id, c.PurchaseExecution.confirm)
EXECUTION_ID = START.next_workflow_id


async def pipeline(binding, trigger, payload, actor, roles):
    result = await workflow.execute_activity(
        "myworkflow.pipeline",
        {
            "binding": binding.id,
            "trigger": trigger.id,
            "payload": PROGRAM.payload(binding, trigger, payload),
            "actor": actor,
            "roles": roles,
        },
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=RetryPolicy(maximum_attempts=1),
    )
    if result["code"] != 0:
        raise ApplicationError(
            "Pipeline rejected", result, type="BusinessRejected", non_retryable=True
        )
    return result


@workflow.defn(name=EXECUTION_ID)
class ConfirmPurchase:
    @workflow.run
    async def run(self, request: dict) -> dict:
        await pipeline(
            TARGET,
            c.PurchaseExecution.confirmation_requested,
            {"application_id": request["application_id"]},
            "system",
            [c.system.id],
        )
        return {"application_id": request["application_id"], "status": "confirmed"}


@workflow.defn(name=APPROVAL_ID)
class ApprovePurchase:
    def __init__(self):
        self.decision = None
        self.phase = "submitting"

    @workflow.signal
    def decide(self, decision: dict):
        if self.decision is None:
            self.decision = decision

    @workflow.query
    def state(self) -> str:
        return self.phase

    @workflow.run
    async def run(self, request: dict) -> dict:
        identity = request["application_id"]
        await pipeline(
            c.PurchaseApproval.submit,
            c.PurchaseApproval.submission,
            {
                "application_id": identity,
                "vendor": request["vendor"],
                "amount": request["amount"],
            },
            request["applicant"],
            [c.requester.id],
        )
        await pipeline(
            c.PurchaseAttachment.upload,
            c.PurchaseAttachment.attachment_received,
            {
                "application_id": identity,
                "quote_a": request["quote_a"],
                "quote_b": request["quote_b"],
            },
            request["applicant"],
            [c.requester.id],
        )
        self.phase = "waiting-approval"
        await workflow.wait_condition(lambda: self.decision is not None)
        decision = self.decision
        result = await pipeline(
            c.PurchaseApproval.approve,
            c.PurchaseApproval.approval_received,
            {"application_id": identity, "decision": decision["approved"]},
            decision["actor"],
            decision["roles"],
        )
        if not decision["approved"]:
            self.phase = "rejected"
            return {"application_id": identity, "status": "rejected"}
        self.phase = "waiting-schedule"
        await workflow.sleep(timedelta(seconds=request.get("delay_seconds", 0)))
        await pipeline(
            START,
            c.PurchaseApproval.scheduled,
            {"application_id": identity},
            "system",
            [c.system.id],
        )
        self.phase = "confirming"
        result = await workflow.execute_child_workflow(
            START.next_workflow_id,
            {"application_id": identity},
            id=f"{workflow.info().workflow_id}/confirm",
        )
        self.phase = "completed"
        return result
