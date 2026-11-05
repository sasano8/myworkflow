"""Shared ticket roles and artifacts."""

from myworkflow import artifact, role
from .value_objects import TicketNumber


@role(id="role.system", name="チケット管理システム", display_name="システム")
class RoleSystem:
    pass


@role(id="ticket.operator", name="窓口担当者", display_name="受付担当")
class RoleOperator:
    pass


@artifact(id="ticket.number", name="受付番号", key="number", value_object=TicketNumber)
class RequestedTicketNumber:
    pass


@artifact(id="ticket.receipt", name="発行結果", key="receipt")
class TicketReceipt:
    pass
