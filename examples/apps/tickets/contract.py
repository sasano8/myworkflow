"""Ticket composition and catalog compilation; SPEC is a compatibility snapshot."""

from myworkflow import binding, pipeline, trigger, workflow
from myworkflow.compiler.declarations import compile_workflows
from .definitions import RoleSystem, RoleOperator, TicketNumber, TicketReceipt
from .steps import number_lock, save_ticket


@pipeline(
    id="ticket.issue",
    name="チケット発行",
    inputs=(TicketNumber,),
    produces=(TicketReceipt,),
    steps=(number_lock, save_ticket),
)
def issue_ticket():
    raise NotImplementedError("The engine executes the declared steps")


@workflow(id="ticket.workflow", name="窓口でのチケット発行")
class TicketIssuance:
    @trigger(
        id="ticket.trigger",
        name="担当者が発行を依頼",
        actor=RoleOperator,
        mapping=((TicketNumber, "受付番号"),),
    )
    class Requested:
        pass

    @binding(
        id="ticket.binding",
        pipeline=issue_ticket,
        triggers=(Requested,),
        roles=(("system", RoleSystem),),
    )
    class Issue:
        pass


compiled = compile_workflows(
    TicketIssuance,
    artifacts=(TicketNumber, TicketReceipt),
    roles=(RoleSystem, RoleOperator),
)
program = compiled.program
SPEC = program.spec
