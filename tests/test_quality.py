"""Round-trip quality tests use frozen source/oracles, never re-create expectations."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import pytest

from myworkflow.scaffold import initialize
from myworkflow.quality import business_to_spec, compare, export_business, source_coverage
from myworkflow.quality.runner import run_case
from myworkflow.quality.rendering import render_quality
from myworkflow.program import Program

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples/apps/purchase/quality'


def test_full_pipeline_and_known_source_gaps_are_explicit():
    report, artifacts = run_case(FIXTURE / 'case.json')
    assert report['passed'], report['failures']
    assert report['metrics']['roundtrip']['exact_match']
    assert report['metrics']['interfaces']['passed']
    assert report['metrics']['skeleton']['passed']
    assert report['metrics']['markdown']['exact_match']
    source = report['metrics']['source']
    assert source['total_units'] == 24
    assert source['counts'] == {'structured': 10, 'description_only': 11, 'missing': 0, 'unrepresented': 3}
    assert source['documented_coverage'] == pytest.approx(21 / 24, rel=0, abs=5e-08)
    assert source['structured_coverage'] == pytest.approx(10 / 24, rel=0, abs=5e-08)
    assert report['judgment'] == 'meets-reviewed-baseline-with-known-gaps'
    assert 'code/interfaces.py' in artifacts
    assert render_quality(report) == (FIXTURE / 'quality-example.md').read_text()


def test_converter_loss_is_not_hidden_by_a_self_consistent_roundtrip():
    def lose_compensation(source):
        document = json.loads((FIXTURE / "business-input.json").read_text())
        del document['steps']['s.put-a']['compensate']
        return document
    report, _ = run_case(FIXTURE / 'case.json', converter=lose_compensation)
    assert not report['passed']
    assert report['metrics']['roundtrip']['recall'] < 1
    assert 'PUR-007' in report['metrics']['source']['new_gaps']
    assert 'c.delete-a' in report['metrics']['skeleton']['missing']
    assert any((d['path'] == '/steps/s.put-a/compensate' for d in report['metrics']['conversion']['missing']))


def test_valid_wrong_type_and_extra_output_are_measured_separately():
    def wrong(source):
        document = json.loads((FIXTURE / "business-input.json").read_text())
        document['artifacts']['a.amount']['type'] = 'str'
        document['artifacts']['a.extra'] = {'name': '余計な情報', 'key': 'extra', 'type': 'str'}
        return document
    report, _ = run_case(FIXTURE / 'case.json', converter=wrong)
    assert not report['passed']
    delta = report['metrics']['roundtrip']
    assert delta['mismatched']
    assert delta['unexpected']
    assert delta['precision'] < 1
    assert not report['metrics']['interfaces']['passed']
    assert report['metrics']['converted_to_code']['exact_match']


def test_order_changes_are_not_treated_as_equivalent():
    def reorder(source):
        document = json.loads((FIXTURE / "business-input.json").read_text())
        steps = document['pipelines']['p.upload']['steps']
        steps[2], steps[3] = steps[3], steps[2]
        return document
    report, _ = run_case(FIXTURE / 'case.json', converter=reorder)
    assert not report['passed']
    assert any(('/pipelines/p.upload/steps/' in d['path'] for d in report['metrics']['roundtrip']['mismatched']))


def test_actual_emitted_interface_is_inspected_not_only_contract_metadata():
    def broken_generator(spec, directory):
        initialize(spec, directory)
        path = directory / 'interfaces.py'
        path.write_text(path.read_text().replace('amount: int', 'amount: str'))
    report, _ = run_case(FIXTURE / 'case.json', generator=broken_generator)
    assert not report['passed']
    assert report['metrics']['roundtrip']['exact_match']
    assert not report['metrics']['interfaces']['passed']
    assert report['metrics']['interfaces']['errors'][0]['class'] == 'PSubmitRequest'


def test_missing_generated_connection_fails():
    def broken_generator(spec, directory):
        initialize(spec, directory)
        path = directory / 'handlers.py'
        path.write_text(path.read_text().replace("@registry.implements('c.delete-a')", '# missing registration'))
    report, _ = run_case(FIXTURE / 'case.json', generator=broken_generator)
    assert not report['passed']
    assert report['metrics']['skeleton']['missing'] == ['c.delete-a']


def test_generator_failure_is_not_success_or_zero_loss():
    def fail(spec, directory): raise OSError('generator failed')
    report, artifacts = run_case(FIXTURE / 'case.json', generator=fail)
    assert not report['passed']
    assert report['stages']['generate'] == 'failed'
    assert report['stages']['export'] == 'not-run'
    assert 'roundtrip' not in report['metrics']
    assert 'business-converted.json' in artifacts


def test_export_reads_immutable_model_not_input_passthrough():
    source = json.loads((FIXTURE / 'business-input.json').read_text())
    program = Program(business_to_spec(source))
    source['artifacts']['a.amount']['type'] = 'str'
    assert export_business(program)['artifacts']['a.amount']['type'] == 'int'
    assert program.model.artifacts[2].type == 'int'


def test_changed_original_requires_inventory_review():
    corpus = json.loads((FIXTURE / 'coverage.json').read_text())
    source = (ROOT / 'docs/requirements/purchase-completion.md').read_text()
    business = json.loads((FIXTURE / 'business-input.json').read_text())
    with pytest.raises(ValueError, match='Source changed'):
        source_coverage(source + '\n追加要件', corpus, business)


def test_unmapped_units_remain_in_denominator_and_invalid_quotes_fail():
    source = (ROOT / 'docs/requirements/purchase-completion.md').read_text()
    corpus = json.loads((FIXTURE / 'coverage.json').read_text())
    business = json.loads((FIXTURE / 'business-input.json').read_text())
    corpus['units'].append({'id': 'UNMAPPED', 'quote': corpus['units'][0]['quote'], 'checks': []})
    result = source_coverage(source, corpus, business)
    assert result['total_units'] == 25
    assert 'UNMAPPED' in result['new_gaps']
    corpus['units'][-1]['quote'] = '原文にない文章'
    with pytest.raises(ValueError): source_coverage(source, corpus, business)


def test_source_inventory_does_not_silently_omit_a_sentence():
    source = (ROOT / 'docs/requirements/purchase-completion.md').read_text()
    corpus = json.loads((FIXTURE / 'coverage.json').read_text())
    business = json.loads((FIXTURE / 'business-input.json').read_text())
    corpus['units'] = [u for u in corpus['units'] if u['id'] != 'PUR-010']
    corpus['accepted_gaps'].remove('PUR-010')
    result = source_coverage(source, corpus, business)
    assert result['source_inventory_coverage'] < 1


def test_exact_comparison_distinguishes_types_empties_and_leaf_categories():
    result = compare({'a': True, 'b': [], 'c': 1}, {'a': 1, 'b': [], 'd': 2})
    assert result['matched_facts'] == 1
    assert len(result['mismatched']) == 1
    assert len(result['missing']) == 1
    assert len(result['unexpected']) == 1
    assert not result['exact_match']
    from myworkflow.quality.metrics import same
    assert not same(['condition', True], ['condition', 1])


def test_duplicate_or_dangling_business_definitions_are_rejected():
    business = json.loads((FIXTURE / 'business-input.json').read_text())
    business['steps']['unused'] = deepcopy(business['steps']['s.submit'])
    with pytest.raises(ValueError, match='unreferenced'):
        business_to_spec(business)


def test_cli_is_repeatable_and_does_not_rewrite_oracles():
    before = {p: p.read_bytes() for p in FIXTURE.iterdir() if p.is_file()}
    with TemporaryDirectory() as temporary:
        command = [sys.executable, '-m', 'myworkflow.quality', '--case', str(FIXTURE / 'case.json'), '--output', temporary]
        for _ in range(2):
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads((Path(temporary) / 'quality.json').read_text())
        assert report['passed']
        assert (Path(temporary) / 'code/interfaces.py').exists()
    assert {p: p.read_bytes() for p in before} == before


def test_cli_saves_failure_report_and_preserves_nonzero_status():
    with TemporaryDirectory() as temporary:
        path = Path(temporary)
        case = json.loads((FIXTURE / 'case.json').read_text())
        for key in ('source', 'business_input', 'expected_markdown', 'coverage', 'sample_conversion'):
            case[key] = str((FIXTURE / case[key]).resolve())
        case['thresholds']['documented_coverage'] = 1.0
        (path / 'case.json').write_text(json.dumps(case))
        result = subprocess.run([sys.executable, '-m', 'myworkflow.quality', '--case', str(path / 'case.json'), '--output', str(path / 'report')], cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 1, result.stdout + result.stderr
        report = json.loads((path / 'report/quality.json').read_text())
        assert not report['passed']
        assert (path / 'report/quality.md').exists()


def test_duplicate_json_keys_are_not_silently_discarded():
    from myworkflow.quality.jsonio import read_json
    with pytest.raises(ValueError, match='Duplicate JSON key'):
        read_json('{"steps":{"s.one":1,"s.one":2}}')


def test_legacy_response_schema_is_not_silently_reinterpreted():
    legacy = json.loads((FIXTURE / 'legacy-v1/business-input.json').read_text())
    with pytest.raises(ValueError, match='schema'):
        business_to_spec(legacy)


def test_changed_completion_contract_is_rejected():
    business = json.loads((FIXTURE / 'business-input.json').read_text())
    business['completion']['success_code'] = False
    with pytest.raises(ValueError, match='completion'):
        business_to_spec(business)


def test_generated_business_response_cannot_masquerade_as_completion():
    def broken_generator(spec, directory):
        initialize(spec, directory)
        path = directory / 'interfaces.py'
        path.write_text(path.read_text().replace('PSubmitResponse = _PipelineResult',
            '@dataclass(frozen=True)\nclass PSubmitResponse:\n    code: int = 0\n    messages: tuple = ()'))
    report, _ = run_case(FIXTURE / 'case.json', generator=broken_generator)
    assert report['metrics']['roundtrip']['exact_match']
    assert not report['metrics']['interfaces']['passed']
    assert report['metrics']['interfaces']['errors'][0]['class'] == 'PSubmitResponse'
