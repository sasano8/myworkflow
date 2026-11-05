"""Ticket step implementations and mutex declaration."""

from myworkflow import declaration, mutex, step
from myworkflow.runtime.context import Context
from .definitions import TicketNumber, TicketReceipt


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
def save_ticket(ctx: Context) -> None:
    number = ctx.values[declaration(TicketNumber).key]
    ctx.services.create_ticket(number)
    ctx.values[declaration(TicketReceipt).key] = "発行済み:" + number
