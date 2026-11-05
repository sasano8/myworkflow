"""compiler behavior and invariants."""

import copy
from dataclasses import FrozenInstanceError
import pytest
from examples.apps.tickets.contract import SPEC
from myworkflow.executable import ContractError, Program


def test_contract_is_immutable_and_uses_one_model():
    source = copy.deepcopy(SPEC)
    program = Program(source)
    source["pipelines"][0]["name"] = "changed"
    snapshot = program.spec
    snapshot["pipelines"][0]["name"] = "also changed"
    assert program.plans["ticket.issue"].name == "チケット発行"
    assert program.catalog().pipelines[0] is program.plans["ticket.issue"]
    with pytest.raises(FrozenInstanceError):
        program.plans["ticket.issue"].name = "bad"
    with pytest.raises(TypeError):
        program.plans["other"] = None


@pytest.mark.parametrize(
    "case_index",
    range(4),
    ids=["empty", "null-artifacts", "invalid-condition", "null-mapping"],
)
def test_malformed_contracts_have_domain_errors(case_index):
    cases = [{}, {"artifacts": None}, copy.deepcopy(SPEC), copy.deepcopy(SPEC)]
    cases[2]["pipelines"][0]["steps"][1]["when"] = [[], True]
    cases[3]["workflows"][0]["bindings"][0]["triggers"][0]["mapping"] = None
    spec = cases[case_index]
    with pytest.raises(ContractError):
        Program(spec)


def test_tested_condition_cannot_be_reassigned():
    spec = copy.deepcopy(SPEC)
    spec["artifacts"].append(
        {"id": "ticket.flag", "name": "判定", "key": "flag", "type": "bool"}
    )
    steps = spec["pipelines"][0]["steps"]
    steps.insert(
        1,
        {
            "id": "ticket.flag-init",
            "name": "判定",
            "summary": "判定",
            "kind": "action",
            "reads": [],
            "writes": ["ticket.flag"],
        },
    )
    steps[2]["when"] = ["ticket.flag", True]
    steps.append(
        {
            "id": "ticket.flag-change",
            "name": "変更",
            "summary": "変更",
            "kind": "action",
            "reads": [],
            "writes": ["ticket.flag"],
        }
    )
    with pytest.raises(ContractError, match="reassigned"):
        Program(spec)
