"""Annotated ticket declarations; SPEC is a generated compatibility snapshot."""

from myworkflow import artifact, binding, mutex, pipeline, role, step, trigger, workflow
from myworkflow.compiler.declarations import compile_workflows


@role(id="role.system", name="チケット管理システム", display_name="システム")
class RoleSystem:
    pass


@role(id="ticket.operator", name="窓口担当者", display_name="受付担当")
class RoleOperator:
    pass


@artifact(id="ticket.number", name="受付番号", key="number")
class TicketNumber:
    pass


@artifact(id="ticket.receipt", name="発行結果", key="receipt")
class TicketReceipt:
    pass


@mutex(id="ticket.lock", name="受付番号の排他", keys=(TicketNumber,))
def number_lock():
    raise NotImplementedError("The engine acquires the declared mutex")


@step(
    id="ticket.save",
    name="チケット保存",
    summary="受付番号を重複なく登録し、発行結果を返す。",
    reads=(TicketNumber,),
    writes=(TicketReceipt,),
    uses=((TicketNumber, "DB作成"), (TicketReceipt, "保持")),
)
def save_ticket(ctx) -> None:
    raise NotImplementedError("Implementation is registered in application.py")


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
