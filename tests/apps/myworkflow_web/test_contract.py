"""Validate requirement traceability and screen entry points before implementation."""

from pathlib import Path
import re

from myworkflow import declaration
from myworkflow.contracts.screens import validate_screens
from examples.apps.myworkflow_web.contract import (
    CATALOG,
    RequirementsDevelopment,
    compiled,
)
from examples.apps.myworkflow_web.screens import SCREENS


def test_all_input_requirements_have_catalog_or_screen_references():
    source = (
        Path(__file__).resolve().parents[3] / "examples/apps/myworkflow_web/README.md"
    )
    requested = set(re.findall(r"^\| (WEB-\d+) \|", source.read_text(), re.MULTILINE))
    declared = {feature.id for screen in SCREENS for feature in screen.features}
    for entity in CATALOG.entities:
        declared.update(entity.extensions.get("requirements", ()))
    assert requested
    assert declared == requested
    # This checks links, not semantic completeness or implemented behavior.


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
