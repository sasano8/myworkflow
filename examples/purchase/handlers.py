"""Handwritten business implementations; generators never overwrite this file."""
from myworkflow.executable import Context, Registry

registry = Registry()


@registry.implements('s.submit')
def submit(ctx: Context) -> None:
    v = ctx.values
    ctx.services.submit(v['application_id'], ctx.actor, v['vendor'], v['amount'])
    v['status'] = 'waiting-approval'


@registry.implements('s.check-upload')
def check_upload(ctx: Context) -> None:
    ctx.services.check_upload(ctx.values['application_id'], ctx.actor)


@registry.implements('s.put-a')
def put_a(ctx: Context) -> None:
    ctx.services.put(ctx.run_id, 'A', ctx.values['quote_a'])


@registry.implements('s.put-b')
def put_b(ctx: Context) -> None:
    ctx.services.put(ctx.run_id, 'B', ctx.values['quote_b'])
    ctx.services.register_attachments(ctx.values['application_id'], ctx.run_id)
    ctx.values['receipt'] = f"attachments-{ctx.run_id}"


@registry.implements('c.delete-a')
def delete_a(ctx: Context) -> None:
    ctx.services.delete(ctx.run_id, 'A')


@registry.implements('c.delete-b')
def delete_b(ctx: Context) -> None:
    ctx.services.delete(ctx.run_id, 'B')


@registry.implements('s.check-approval')
def check_approval(ctx: Context) -> None:
    app = ctx.services.application(ctx.values['application_id'])
    if app['status'] != 'waiting-approval':
        raise ValueError('Application is not awaiting approval')
    if app['owner'] == ctx.actor:
        raise PermissionError('Applicant cannot approve their own application')


@registry.implements('s.approve')
def approve(ctx: Context) -> None:
    ctx.values['status'] = ctx.services.decide(ctx.values['application_id'], ctx.actor, True)


@registry.implements('s.reject')
def reject(ctx: Context) -> None:
    ctx.values['status'] = ctx.services.decide(ctx.values['application_id'], ctx.actor, False)


@registry.implements('s.dispatch')
def dispatch(ctx: Context) -> None:
    if ctx.services.application(ctx.values['application_id'])['status'] != 'approved':
        raise ValueError('Only approved applications can start order confirmation')


@registry.implements('s.eligibility')
def eligibility(ctx: Context) -> None:
    ctx.values['eligible'] = ctx.services.eligible(ctx.values['application_id'])


@registry.implements('s.confirm')
def confirm(ctx: Context) -> None:
    ctx.values['order_id'] = ctx.services.confirm(ctx.values['application_id'])


@registry.implements('s.stop')
def stop(ctx: Context) -> None:
    raise ValueError('Order conditions are not satisfied')
