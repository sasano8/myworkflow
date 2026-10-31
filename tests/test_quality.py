"""Round-trip quality tests use frozen source/oracles, never re-create expectations."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from myworkflow.scaffold import initialize
from myworkflow.quality import business_to_spec, compare, export_business, source_coverage
from myworkflow.quality.runner import run_case
from myworkflow.quality.rendering import render_quality
from myworkflow.program import Program

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples/purchase/quality'


class QualityTests(unittest.TestCase):
    def test_full_pipeline_and_known_source_gaps_are_explicit(self):
        report, artifacts = run_case(FIXTURE / 'case.json')
        self.assertTrue(report['passed'], report['failures'])
        self.assertTrue(report['metrics']['roundtrip']['exact_match'])
        self.assertTrue(report['metrics']['interfaces']['passed'])
        self.assertTrue(report['metrics']['skeleton']['passed'])
        self.assertTrue(report['metrics']['markdown']['exact_match'])
        source = report['metrics']['source']
        self.assertEqual(source['total_units'], 23)
        self.assertEqual(source['counts'], {'structured': 9, 'description_only': 11, 'missing': 0, 'unrepresented': 3})
        self.assertAlmostEqual(source['documented_coverage'], 20 / 23)
        self.assertAlmostEqual(source['structured_coverage'], 9 / 23)
        self.assertEqual(report['judgment'], 'meets-reviewed-baseline-with-known-gaps')
        self.assertIn('code/interfaces.py', artifacts)
        self.assertEqual(render_quality(report), (FIXTURE / 'quality-example.md').read_text())

    def test_converter_loss_is_not_hidden_by_a_self_consistent_roundtrip(self):
        def lose_compensation(source):
            document = json.loads((FIXTURE / "business-input.json").read_text())
            del document['steps']['s.put-a']['compensate']
            return document
        report, _ = run_case(FIXTURE / 'case.json', converter=lose_compensation)
        self.assertFalse(report['passed'])
        self.assertLess(report['metrics']['roundtrip']['recall'], 1)
        self.assertIn('PUR-007', report['metrics']['source']['new_gaps'])
        self.assertIn('c.delete-a', report['metrics']['skeleton']['missing'])
        self.assertTrue(any(d['path'] == '/steps/s.put-a/compensate' for d in report['metrics']['conversion']['missing']))

    def test_valid_wrong_type_and_extra_output_are_measured_separately(self):
        def wrong(source):
            document = json.loads((FIXTURE / "business-input.json").read_text())
            document['artifacts']['a.amount']['type'] = 'str'
            document['artifacts']['a.extra'] = {'name': '余計な情報', 'key': 'extra', 'type': 'str'}
            return document
        report, _ = run_case(FIXTURE / 'case.json', converter=wrong)
        self.assertFalse(report['passed'])
        delta = report['metrics']['roundtrip']
        self.assertTrue(delta['mismatched'])
        self.assertTrue(delta['unexpected'])
        self.assertLess(delta['precision'], 1)
        self.assertFalse(report['metrics']['interfaces']['passed'])
        self.assertTrue(report['metrics']['converted_to_code']['exact_match'])

    def test_order_changes_are_not_treated_as_equivalent(self):
        def reorder(source):
            document = json.loads((FIXTURE / "business-input.json").read_text())
            steps = document['pipelines']['p.upload']['steps']
            steps[2], steps[3] = steps[3], steps[2]
            return document
        report, _ = run_case(FIXTURE / 'case.json', converter=reorder)
        self.assertFalse(report['passed'])
        self.assertTrue(any('/pipelines/p.upload/steps/' in d['path'] for d in report['metrics']['roundtrip']['mismatched']))

    def test_actual_emitted_interface_is_inspected_not_only_contract_metadata(self):
        def broken_generator(spec, directory):
            initialize(spec, directory)
            path = directory / 'interfaces.py'
            path.write_text(path.read_text().replace('amount: int', 'amount: str'))
        report, _ = run_case(FIXTURE / 'case.json', generator=broken_generator)
        self.assertFalse(report['passed'])
        self.assertTrue(report['metrics']['roundtrip']['exact_match'])
        self.assertFalse(report['metrics']['interfaces']['passed'])
        self.assertEqual(report['metrics']['interfaces']['errors'][0]['class'], 'PSubmitRequest')

    def test_missing_generated_connection_fails(self):
        def broken_generator(spec, directory):
            initialize(spec, directory)
            path = directory / 'handlers.py'
            path.write_text(path.read_text().replace("@registry.implements('c.delete-a')", '# missing registration'))
        report, _ = run_case(FIXTURE / 'case.json', generator=broken_generator)
        self.assertFalse(report['passed'])
        self.assertEqual(report['metrics']['skeleton']['missing'], ['c.delete-a'])

    def test_generator_failure_is_not_success_or_zero_loss(self):
        def fail(spec, directory): raise OSError('generator failed')
        report, artifacts = run_case(FIXTURE / 'case.json', generator=fail)
        self.assertFalse(report['passed'])
        self.assertEqual(report['stages']['generate'], 'failed')
        self.assertEqual(report['stages']['export'], 'not-run')
        self.assertNotIn('roundtrip', report['metrics'])
        self.assertIn('business-converted.json', artifacts)

    def test_export_reads_immutable_model_not_input_passthrough(self):
        source = json.loads((FIXTURE / 'business-input.json').read_text())
        program = Program(business_to_spec(source))
        source['artifacts']['a.amount']['type'] = 'str'
        self.assertEqual(export_business(program)['artifacts']['a.amount']['type'], 'int')
        self.assertEqual(program.model.artifacts[2].type, 'int')

    def test_changed_original_requires_inventory_review(self):
        corpus = json.loads((FIXTURE / 'coverage.json').read_text())
        source = (ROOT / 'docs/requirements/purchase.md').read_text()
        business = json.loads((FIXTURE / 'business-input.json').read_text())
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            source_coverage(source + '\n追加要件', corpus, business)

    def test_unmapped_units_remain_in_denominator_and_invalid_quotes_fail(self):
        source = (ROOT / 'docs/requirements/purchase.md').read_text()
        corpus = json.loads((FIXTURE / 'coverage.json').read_text())
        business = json.loads((FIXTURE / 'business-input.json').read_text())
        corpus['units'].append({'id': 'UNMAPPED', 'quote': corpus['units'][0]['quote'], 'checks': []})
        result = source_coverage(source, corpus, business)
        self.assertEqual(result['total_units'], 24)
        self.assertIn('UNMAPPED', result['new_gaps'])
        corpus['units'][-1]['quote'] = '原文にない文章'
        with self.assertRaises(ValueError): source_coverage(source, corpus, business)

    def test_source_inventory_does_not_silently_omit_a_sentence(self):
        source = (ROOT / 'docs/requirements/purchase.md').read_text()
        corpus = json.loads((FIXTURE / 'coverage.json').read_text())
        business = json.loads((FIXTURE / 'business-input.json').read_text())
        corpus['units'] = [u for u in corpus['units'] if u['id'] != 'PUR-010']
        corpus['accepted_gaps'].remove('PUR-010')
        result = source_coverage(source, corpus, business)
        self.assertLess(result['source_inventory_coverage'], 1)

    def test_exact_comparison_distinguishes_types_empties_and_leaf_categories(self):
        result = compare({'a': True, 'b': [], 'c': 1}, {'a': 1, 'b': [], 'd': 2})
        self.assertEqual(result['matched_facts'], 1)
        self.assertEqual(len(result['mismatched']), 1)
        self.assertEqual(len(result['missing']), 1)
        self.assertEqual(len(result['unexpected']), 1)
        self.assertFalse(result['exact_match'])
        from myworkflow.quality.metrics import same
        self.assertFalse(same(['condition', True], ['condition', 1]))

    def test_duplicate_or_dangling_business_definitions_are_rejected(self):
        business = json.loads((FIXTURE / 'business-input.json').read_text())
        business['steps']['unused'] = deepcopy(business['steps']['s.submit'])
        with self.assertRaisesRegex(ValueError, 'unreferenced'):
            business_to_spec(business)

    def test_cli_is_repeatable_and_does_not_rewrite_oracles(self):
        before = {p: p.read_bytes() for p in FIXTURE.iterdir() if p.is_file()}
        with TemporaryDirectory() as temporary:
            command = [sys.executable, '-m', 'myworkflow.quality', '--case', str(FIXTURE / 'case.json'), '--output', temporary]
            for _ in range(2):
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((Path(temporary) / 'quality.json').read_text())
            self.assertTrue(report['passed'])
            self.assertTrue((Path(temporary) / 'code/interfaces.py').exists())
        self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_cli_saves_failure_report_and_preserves_nonzero_status(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary)
            case = json.loads((FIXTURE / 'case.json').read_text())
            for key in ('source', 'business_input', 'expected_markdown', 'coverage', 'sample_conversion'):
                case[key] = str((FIXTURE / case[key]).resolve())
            case['thresholds']['documented_coverage'] = 1.0
            (path / 'case.json').write_text(json.dumps(case))
            result = subprocess.run([sys.executable, '-m', 'myworkflow.quality', '--case', str(path / 'case.json'), '--output', str(path / 'report')], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((path / 'report/quality.json').read_text())
            self.assertFalse(report['passed'])
            self.assertTrue((path / 'report/quality.md').exists())

    def test_duplicate_json_keys_are_not_silently_discarded(self):
        from myworkflow.quality.jsonio import read_json
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            read_json('{"steps":{"s.one":1,"s.one":2}}')
