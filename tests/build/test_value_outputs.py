"""Value-object build behavior."""
from myworkflow.generation.documents import document_program
import json
from pathlib import Path
import pytest
from examples.feature_demos.approval_values import application as sample
from examples.feature_demos.approval_values.build import BUILD
from myworkflow.build.cli import build, compile_outputs
from myworkflow.generation.data_definitions import render_data_definitions

ROOT = Path(__file__).resolve().parents[2]


def test_build_includes_separate_data_files_and_detects_constraint_drift(tmp_path):
    outputs = build(BUILD, tmp_path, target='temporal')
    assert outputs['data-definitions.md'] == render_data_definitions(sample.compiled.catalog)
    assert json.loads(outputs['build.json'])['files']['data-definitions.json']
    build(BUILD, tmp_path, target='temporal', check=True)
    target = tmp_path / 'data-definitions.json'
    target.write_text('{}')
    with pytest.raises(ValueError, match='stale'):
        build(BUILD, tmp_path, target='temporal', check=True)
    assert target.read_text() == '{}'



def test_purchase_owns_value_definitions_and_builds_frozen_documents():
    from examples.apps.purchase import contract, value_objects
    from examples.apps.purchase.build import BUILD as purchase_build
    assert contract.amount.value_object is value_objects.amount_type
    assert contract.vendor.value_object is value_objects.vendor_type
    assert contract.application_id.value_object is value_objects.application_id_type
    outputs = compile_outputs(purchase_build, target='temporal')
    for name in ('data-definitions.md', 'data-definitions.json'):
        assert outputs[name] == (ROOT / 'examples/apps/purchase/docs' / name).read_text()
    assert 'data-definitions.md#vo.purchase.amount' in document_program(contract.program)
    from myworkflow.acceptance.rendering import DocumentOptions, render_business
    options = DocumentOptions(data_definitions_link='../data-definitions.md')
    assert '../data-definitions.md#vo.purchase.amount' in render_business(contract.program, None, (), options=options)
