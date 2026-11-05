"""Value-object contracts behavior."""

from datetime import date
import pytest
from pydantic import Field, ValidationError
from examples.feature_demos.approval_values.value_objects import (
    DeliveryPeriod,
    PurchaseAmount,
    approval_application,
    delivery_period,
    purchase_amount,
)
from myworkflow import ValueModel, ValueObject
from myworkflow.contracts.errors import ContractError


@pytest.mark.parametrize("value", [0, -1, 1.5, True, "100", float("nan")])
def test_money_rejects_invalid_or_ambiguous_values(value):
    with pytest.raises(ContractError, match="invalid value"):
        purchase_amount.normalize(value)


def test_models_are_frozen_and_validation_cannot_be_bypassed_with_construct():
    amount = PurchaseAmount(100)
    assert purchase_amount.normalize(amount) == 100
    with pytest.raises(ValidationError):
        amount.root = 200
    with pytest.raises(ContractError):
        purchase_amount.normalize(PurchaseAmount.model_construct(root=-100))
    assert (
        approval_application.normalize(
            {"owner": "alice", "amount": 100, "status": "waiting"}
        )["approved_by"]
        is None
    )
    with pytest.raises(ContractError):
        approval_application.normalize(
            {"owner": "alice", "amount": 100, "status": "waiting", "unknown": True}
        )


def test_cross_field_rule_runs_but_is_not_claimed_as_json_schema_constraint():
    assert delivery_period.normalize(
        DeliveryPeriod(starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 1))
    ) == {"starts_on": "2026-01-01", "ends_on": "2026-01-01"}
    with pytest.raises(ContractError, match="終了日"):
        delivery_period.normalize({"starts_on": "2026-11-30", "ends_on": "2026-11-01"})
    definition = delivery_period.definition()
    assert definition["rules"] == ["終了日は開始日以降とする。同日も許可する。"]
    assert definition["validators"] == [
        {"name": "dates_in_order", "kind": "model_validators", "fields": []}
    ]
    assert definition["schema"]["properties"]["starts_on"]["format"] == "date"


def test_nested_models_and_input_aliases_are_visible_in_data_definition():
    class Nested(DeliveryPeriod):
        pass

    class Envelope(ValueModel):
        period: Nested = Field(alias="deliveryWindow", description="納品受付期間。")

    definition = ValueObject("vo.envelope", "納品情報", Envelope)
    details = definition.definition()
    assert "Nested" in details["schema"]["$defs"]
    assert details["input_aliases"] == {"period": "deliveryWindow"}
    assert any(v.get("model", "").endswith(".Nested") for v in details["validators"])
    expected = {"period": {"starts_on": "2026-01-01", "ends_on": "2026-02-01"}}
    assert definition.normalize({"deliveryWindow": expected["period"]}) == expected
    assert definition.normalize(expected) == expected
