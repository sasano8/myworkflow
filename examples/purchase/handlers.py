"""Handwritten business implementations; generators never overwrite this file."""
from myworkflow.executable import BusinessError, Context, Registry
from examples.purchase import contract as c

registry = Registry()


@registry.implements(c.save_application)
def submit(ctx: Context) -> None:
    v = ctx.values
    ctx.services.submit(v[c.application_id.key], ctx.actor, v[c.vendor.key], v[c.amount.key])
    v[c.application_status.key] = 'waiting-approval'
    ctx.add_message('申請を受け付けました')


@registry.implements(c.check_attachment)
def check_upload(ctx: Context) -> None:
    ctx.services.check_upload(ctx.values[c.application_id.key], ctx.actor)


@registry.implements(c.save_quote_a)
def put_a(ctx: Context) -> None:
    ctx.services.put(ctx.run_id, 'A', ctx.values[c.quote_a.key])


@registry.implements(c.save_quote_b)
def put_b(ctx: Context) -> None:
    ctx.services.put(ctx.run_id, 'B', ctx.values[c.quote_b.key])
    ctx.services.register_attachments(ctx.values[c.application_id.key], ctx.run_id)
    ctx.values[c.attachment_receipt.key] = f"attachments-{ctx.run_id}"


@registry.implements(c.delete_quote_a)
def delete_a(ctx: Context) -> None:
    ctx.services.delete(ctx.run_id, 'A')


@registry.implements(c.delete_quote_b)
def delete_b(ctx: Context) -> None:
    ctx.services.delete(ctx.run_id, 'B')


@registry.implements(c.check_approval)
def check_approval(ctx: Context) -> None:
    app = ctx.services.application(ctx.values[c.application_id.key])
    if app['status'] != 'waiting-approval':
        raise ValueError('Application is not awaiting approval')
    if app['owner'] == ctx.actor:
        raise PermissionError('Applicant cannot approve their own application')


@registry.implements(c.approve_application)
def approve(ctx: Context) -> None:
    ctx.values[c.application_status.key] = ctx.services.decide(ctx.values[c.application_id.key], ctx.actor, True)


@registry.implements(c.reject_application)
def reject(ctx: Context) -> None:
    ctx.values[c.application_status.key] = ctx.services.decide(ctx.values[c.application_id.key], ctx.actor, False)


@registry.implements(c.check_handoff)
def dispatch(ctx: Context) -> None:
    if ctx.services.application(ctx.values[c.application_id.key])['status'] != 'approved':
        raise ValueError('Only approved applications can start order confirmation')


@registry.implements(c.check_eligibility)
def eligibility(ctx: Context) -> None:
    ctx.values[c.eligible.key] = ctx.services.eligible(ctx.values[c.application_id.key])


@registry.implements(c.confirm_order)
def confirm(ctx: Context) -> None:
    ctx.values[c.order_id.key] = ctx.services.confirm(ctx.values[c.application_id.key])


@registry.implements(c.reject_order)
def stop(ctx: Context) -> None:
    raise BusinessError(10, 'Order conditions are not satisfied', level='warning')
