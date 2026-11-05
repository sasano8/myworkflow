"""Value types, independent of where they are used in the workflow."""

from typing import Annotated
from pydantic import ConfigDict, Field, RootModel
from myworkflow import value_object


@value_object(
    id="vo.ticket.number",
    name="受付番号",
    description="受付番号を文字列として扱う。書式・長さ・空文字の制約は未定義。",
)
class TicketNumber(
    RootModel[
        Annotated[
            str, Field(description="チケットを識別する受付番号。", examples=["T-001"])
        ]
    ]
):
    model_config = ConfigDict(frozen=True, strict=True, validate_default=True)
