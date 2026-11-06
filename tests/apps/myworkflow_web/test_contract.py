"""Validate requirement traceability and screen entry points before implementation."""

import pytest

from myworkflow.contracts.errors import ContractError
from examples.apps.myworkflow_web import requirements as r
from examples.apps.myworkflow_web.documentation import requirement_references

from myworkflow import declaration
from myworkflow.contracts.screens import validate_screens
from examples.apps.myworkflow_web.contract import (
    CATALOG,
    RequirementsDevelopment,
    compiled,
)
from examples.apps.myworkflow_web.screens import SCREENS


def test_all_annotated_requirements_have_catalog_or_screen_references():
    references = requirement_references(CATALOG, SCREENS)
    assert set(references) == {declaration(target).id for target in r.REQUIREMENTS}


def test_annotation_missing_from_inventory_is_rejected(monkeypatch):
    monkeypatch.setattr(r, "REQUIREMENTS", r.REQUIREMENTS[1:])
    with pytest.raises(ContractError, match="registered once"):
        requirement_references(CATALOG, SCREENS)


def test_new_requirement_without_screen_or_step_reference_is_rejected(monkeypatch):
    @r.requirement(id="WEB-new", name="追加要件", summary="対応先がまだない")
    class NewRequirement:
        pass

    monkeypatch.setattr(r, "NewRequirement", NewRequirement, raising=False)
    monkeypatch.setattr(r, "REQUIREMENTS", (*r.REQUIREMENTS, NewRequirement))
    with pytest.raises(ContractError, match="missing=.*WEB-new"):
        requirement_references(CATALOG, SCREENS)


def test_screen_calls_belong_to_the_declared_workflows():
    validate_screens(SCREENS, CATALOG)


def test_auto_and_manual_build_share_pipeline_but_keep_distinct_triggers():
    workflow = compiled.workflow(RequirementsDevelopment)
    binding = next(
        b
        for b in workflow.bindings
        if b.id == declaration(RequirementsDevelopment.build).id
    )
    manual, automatic = binding.triggers
    assert binding.pipeline_id == "web.p.build"
    assert manual.after is None
    assert manual.actor_role_id == "web.role.user"
    assert automatic.after == declaration(RequirementsDevelopment.revise).id
    assert automatic.actor_role_id == "web.role.system"
