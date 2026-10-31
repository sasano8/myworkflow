"""Optional Temporal experiment; storage and authorization are not implemented."""
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError


@activity.defn(name="s.confirm-order")
async def confirm_order(request: dict) -> dict:
    if not request.get("approved") or not request.get("quote_registered"):
        raise ApplicationError("Approval and quotation are required", non_retryable=True)
    # Demonstration result only: this does not write an order to a database.
    return {"application_id": request["application_id"], "status": "confirmed-demo"}


@workflow.defn(name="w.execution")
class ConfirmPurchase:
    @workflow.run
    async def run(self, request: dict) -> dict:
        return await workflow.execute_activity(
            "s.confirm-order", request, start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )


@workflow.defn(name="w.approval")
class ApprovePurchase:
    def __init__(self):
        self.approved = False
        self.phase = "waiting-approval"

    @workflow.signal
    def approve(self):
        self.approved = True

    @workflow.query
    def state(self) -> str:
        return self.phase

    @workflow.run
    async def run(self, request: dict) -> dict:
        await workflow.wait_condition(lambda: self.approved)
        self.phase = "waiting-schedule"
        await workflow.sleep(timedelta(seconds=request.get("delay_seconds", 0)))
        self.phase = "confirming"
        result = await workflow.execute_child_workflow(
            "w.execution", {**request, "approved": True},
            id=f"{workflow.info().workflow_id}/w.execution",
        )
        self.phase = "completed"
        return result
