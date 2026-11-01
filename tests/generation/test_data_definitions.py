"""Value-object generation behavior."""
from myworkflow.generation.documents import document_program
from pathlib import Path
from examples.feature_demos.approval_values import application as sample
from examples.feature_demos.approval_values.build import BUILD
from myworkflow.build.cli import compile_outputs
from myworkflow.generation.data_definitions import data_definitions_source, render_data_definitions

ROOT = Path(__file__).resolve().parents[2]


def test_independent_data_documents_match_reviewed_samples_and_business_links():
    catalog = sample.compiled.catalog
    markdown = render_data_definitions(catalog)
    assert markdown == (ROOT / 'examples/feature_demos/approval_values/docs/data-definitions.md').read_text()
    assert data_definitions_source(catalog) == (ROOT / 'examples/feature_demos/approval_values/docs/data-definitions.json').read_text()
    assert 'JSON Schemaだけでは全条件を表せない' in markdown
    assert '0より大きい' in markdown
    assert '```' not in markdown
    assert 'exclusiveMinimum' in data_definitions_source(catalog)
    assert 'data-definitions.md#vo.application_id' in document_program(sample.compiled.program)
    assert 'exclusiveMinimum' not in document_program(sample.compiled.program)
    assert compile_outputs(BUILD, target='temporal')['requirements.md'] == (ROOT / 'examples/feature_demos/approval_values/docs/requirements.md').read_text()
