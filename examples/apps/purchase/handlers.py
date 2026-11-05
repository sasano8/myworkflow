"""Handwritten business implementations; generators never overwrite this file."""

from myworkflow import annotate
from myworkflow.executable import BusinessError, Context, Registry
from examples.apps.purchase import contract as c


@annotate(c.save_application)
def submit(ctx: Context) -> None:
    v = ctx.values
    ctx.services.submit(
        v[c.application_id.key], ctx.actor, v[c.vendor.key], v[c.amount.key]
    )
    v[c.application_status.key] = "waiting-approval"
    ctx.add_message("申請を受け付けました")


@annotate(c.check_attachment)
def check_upload(ctx: Context) -> None:
    ctx.services.check_upload(ctx.values[c.application_id.key], ctx.actor)


@annotate(c.save_quote_a)
def put_a(ctx: Context) -> None:
    ctx.services.put(ctx.run_id, "A", ctx.values[c.quote_a.key])


@annotate(c.save_quote_b)
def put_b(ctx: Context) -> None:
    ctx.services.put(ctx.run_id, "B", ctx.values[c.quote_b.key])
    ctx.services.register_attachments(ctx.values[c.application_id.key], ctx.run_id)
    ctx.values[c.attachment_receipt.key] = f"attachments-{ctx.run_id}"


@annotate(c.delete_quote_a)
def delete_a(ctx: Context) -> None:
    ctx.services.delete(ctx.run_id, "A")


@annotate(c.delete_quote_b)
def delete_b(ctx: Context) -> None:
    ctx.services.delete(ctx.run_id, "B")


@annotate(c.check_approval)
def check_approval(ctx: Context) -> None:
    app = ctx.services.application(ctx.values[c.application_id.key])
    if app["status"] != "waiting-approval":
        raise ValueError("Application is not awaiting approval")
    if app["owner"] == ctx.actor:
        raise PermissionError("Applicant cannot approve their own application")


@annotate(c.approve_application)
def approve(ctx: Context) -> None:
    ctx.values[c.application_status.key] = ctx.services.decide(
        ctx.values[c.application_id.key], ctx.actor, True
    )


@annotate(c.reject_application)
def reject(ctx: Context) -> None:
    ctx.values[c.application_status.key] = ctx.services.decide(
        ctx.values[c.application_id.key], ctx.actor, False
    )


@annotate(c.check_handoff)
def dispatch(ctx: Context) -> None:
    if (
        ctx.services.application(ctx.values[c.application_id.key])["status"]
        != "approved"
    ):
        raise ValueError("Only approved applications can start order confirmation")


@annotate(c.check_eligibility)
def eligibility(ctx: Context) -> None:
    ctx.values[c.eligible.key] = ctx.services.eligible(ctx.values[c.application_id.key])


@annotate(c.confirm_order)
def confirm(ctx: Context) -> None:
    ctx.values[c.order_id.key] = ctx.services.confirm(ctx.values[c.application_id.key])


@annotate(c.reject_order)
def stop(ctx: Context) -> None:
    raise BusinessError(10, "Order conditions are not satisfied", level="warning")


registry = Registry()
for implementation in (
    submit,
    check_upload,
    put_a,
    put_b,
    delete_a,
    delete_b,
    check_approval,
    approve,
    reject,
    dispatch,
    eligibility,
    confirm,
    stop,
):
    registry.register(implementation)
