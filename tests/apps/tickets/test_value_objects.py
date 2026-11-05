"""Ticket value types validate inputs without changing context's JSON representation."""

import pytest

from myworkflow import declaration
from myworkflow.contracts.errors import ContractError
from examples.apps.tickets.contract import program
from examples.apps.tickets.definitions import RequestedTicketNumber
from examples.apps.tickets.value_objects import TicketNumber


def test_ticket_number_type_is_attached_to_the_input_artifact():
    definition = declaration(TicketNumber)
    assert declaration(RequestedTicketNumber).value_object is definition
    assert definition.model is TicketNumber
    assert program.model.value_objects == (definition,)
    assert program.values(
        ("ticket.number",), {"number": TicketNumber("T-001")}, "input"
    ) == {"number": "T-001"}


@pytest.mark.parametrize("value", [123, True, None, {"root": "T-001"}])
def test_invalid_ticket_number_types_are_rejected(value):
    with pytest.raises(ContractError, match="invalid value"):
        program.values(("ticket.number",), {"number": value}, "input")
