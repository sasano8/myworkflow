"""Value-object compiler behavior."""

from dataclasses import replace
import json
import pytest
from examples.feature_demos.approval_values import application as sample
from examples.feature_demos.approval_values.value_objects import application_identifier
from myworkflow.compiler.declarations import compile_workflows
from myworkflow.contracts.errors import ContractError
from myworkflow.compiler.program import Program
from myworkflow.generation.business import business_to_spec, export_business


def test_registry_identity_and_primitive_shape_are_checked():
    with pytest.raises(ContractError, match="different objects"):
        compile_workflows(
            sample.Approval,
            artifacts=(sample.application_id,),
            value_objects=(replace(application_identifier),),
        )
    catalog = sample.compiled.catalog
    with pytest.raises(ContractError, match="JSON type"):
        Program.from_catalog(
            replace(catalog, artifacts=(replace(sample.application_id, type="int"),))
        )
    with pytest.raises(ContractError, match="unique"):
        Program.from_catalog(
            replace(
                catalog, value_objects=(*catalog.value_objects, application_identifier)
            )
        )


def test_export_roundtrip_requires_explicit_models_and_never_imports_document_paths():
    program = sample.compiled.program
    business = export_business(program)
    spec = business_to_spec(business)
    with pytest.raises(ContractError, match="explicit Python"):
        Program(spec)
    rebuilt = Program(spec, value_objects=sample.compiled.catalog.value_objects)
    assert export_business(rebuilt) == business
    changed = json.loads(json.dumps(spec))
    changed["value_objects"][0]["schema"]["pattern"] = "different"
    with pytest.raises(ContractError, match="explicit Python"):
        Program(changed, value_objects=sample.compiled.catalog.value_objects)
