"""Shared ticket roles and artifacts."""

from myworkflow import artifact, role


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
