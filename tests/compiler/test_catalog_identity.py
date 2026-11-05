"""Catalog identity survives compilation, compatibility snapshots and business IR."""

from dataclasses import replace
import json

from examples.apps.purchase.build import BUILD
from examples.feature_demos.declarative_review.contract import (
    ApplicationReview,
    application_id,
    decision,
)
from examples.feature_demos.product_catalogs.insurance import CATALOG
from myworkflow.build import compile_outputs
from myworkflow.compiler.declarations import compile_workflows
from myworkflow.compiler.program import Program
from myworkflow.generation.business import business_to_spec, export_business


def test_catalog_identity_round_trips_through_spec_and_business_document():
    program = Program.from_catalog(CATALOG)
    assert program.spec["id"] == CATALOG.id
    restored = Program(program.spec)
    assert (restored.model.id, restored.model.name) == (CATALOG.id, CATALOG.name)
    business = export_business(program)
    assert business["catalog"] == {"id": CATALOG.id, "name": CATALOG.name}
    restored = Program(business_to_spec(business))
    assert restored.model == CATALOG


def test_symbolic_compilation_can_name_the_requirement_catalog():
    compiled = compile_workflows(
        ApplicationReview,
        artifacts=(application_id, decision),
        catalog_id="product.review",
        catalog_name="審査商品",
    )
    assert compiled.catalog.id == "product.review"
    assert compiled.program.spec["name"] == "審査商品"


def test_build_selection_preserves_catalog_metadata():
    program = Program.from_catalog(
        replace(BUILD.compiled.catalog, id="product.purchase", name="購買商品")
    )
    config = replace(BUILD, compiled=replace(BUILD.compiled, program=program))
    outputs = compile_outputs(config, target="kestra", workflows=("w.attach",))
    assert json.loads(outputs["ir.json"])["business"]["catalog"] == {
        "id": "product.purchase",
        "name": "購買商品",
    }
    assert "購買商品（product.purchase）" in outputs["requirements.md"]
