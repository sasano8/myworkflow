"""Tool tests; actual business acceptance cases live in tests/acceptance."""
from dataclasses import replace
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pytest_bdd import parsers

from examples.purchase.acceptance.catalog import DIRECTORY, DOCUMENTS, cases, program, registry, steps
from examples.purchase.acceptance.world import World
from myworkflow.acceptance import Definitions, load_cases, render_business, render_cases, render_report
from myworkflow.executable import Program

ROOT = Path(__file__).resolve().parents[2]


def load_text(tmp_path, text, definitions=steps, target=program):
    path = tmp_path / 'test.feature'
    path.write_text(text, encoding='utf-8')
    return load_cases([path], target, definitions)


def test_docs_match_canonical_features():
    catalog = cases()
    assert len(catalog) == 14
    assert len([c for c in catalog if c.scenario_id == 'scenario.purchase.upload']) == 6
    assert render_cases(catalog, steps, options=DOCUMENTS) == (DIRECTORY / 'acceptance.md').read_text()
    assert render_business(program, registry, catalog, options=DOCUMENTS) == (DIRECTORY / 'business.md').read_text()


def test_python_declaration_and_gherkin_express_same_small_case(tmp_path):
    python_steps = [('Context', '見積書のない承認待ちの購買申請がある'), ('Outcome', '発注は0件である')]
    text = '''機能: 比較
  @scenario.compare @req.p.submit
  シナリオ: 比較例
    前提 見積書のない承認待ちの購買申請がある
    ならば 発注は0件である
'''
    case = load_text(tmp_path, '# language: ja\n' + text)[0]
    assert [(s['type'], s['text']) for s in case.steps] == python_steps
    world = World(tmp_path)
    try:
        for kind, text in python_steps:
            definition = steps.resolve(kind, text)
            result = definition.function(ctx=world, **definition.parser.parse_arguments(text))
            if kind == 'Outcome':
                assert result is True
    finally:
        world.close()


@pytest.mark.parametrize('change', ['unknown-reference', 'missing-operation', 'missing-outcome', 'duplicate-case', 'duplicate-scenario'])
def test_invalid_scenarios_fail_before_execution(tmp_path, change):
    source = (DIRECTORY / 'features/purchase.feature').read_text()
    if change == 'unknown-reference':
        source = source.replace('@req.p.confirm', '@req.p.missing')
    elif change == 'missing-operation':
        source = source.replace('発注は0件である', '未登録の操作')
    elif change == 'missing-outcome':
        source = '# language: ja\n機能: 空\n  @scenario.empty @req.p.submit\n  シナリオ: 空\n    前提 見積書のない承認待ちの購買申請がある\n'
    elif change == 'duplicate-case':
        source = source.replace('| first-failure |', '| success       |')
    else:
        source = source.replace('@scenario.purchase.reject', '@scenario.purchase.schedule')
    with pytest.raises(ValueError):
        load_text(tmp_path, source)


def test_ambiguous_operation_is_rejected(tmp_path):
    definitions = Definitions()
    definitions.items = [*steps.items, steps.items[0]]
    with pytest.raises(ValueError, match='found 2'):
        load_text(tmp_path, (DIRECTORY / 'features/purchase.feature').read_text(), definitions)


def test_empty_verification_is_not_success():
    definitions = Definitions()
    @definitions.step('Outcome', parsers.parse('empty'), actor='検証', refs=('p.submit',))
    def empty(ctx):
        pass
    with pytest.raises(AssertionError, match='expected True'):
        empty(None)


def test_rename_and_row_reorder_preserve_ids(tmp_path):
    source = (DIRECTORY / 'features/purchase.feature').read_text()
    rows = source.splitlines()
    a = next(i for i, line in enumerate(rows) if '| success ' in line)
    rows[a], rows[a + 1] = rows[a + 1], rows[a]
    changed = load_text(tmp_path, '\n'.join(rows))
    original = load_text(tmp_path, source)
    assert {c.id for c in original} == {c.id for c in changed}
    spec = copy.deepcopy(program.spec)
    spec['pipelines'][4]['name'] = '新しい発注名'
    text = render_business(Program(spec, value_objects=program.model.value_objects), registry, changed)
    assert '新しい発注名' in text
    assert 'scenario.purchase.schedule' in text
    assert 'w.execution/b.confirm/p.confirm/s.confirm' in text


def test_document_escapes_customer_text():
    case = replace(cases()[0], name='申請|<script>\nテスト')
    text = render_cases([case], steps)
    assert '申請&#124;&lt;script&gt;<br>テスト' in text
    assert '<script>' not in text


def test_check_mode_does_not_rewrite_sources():
    sources = [*DIRECTORY.glob('features/*.feature'), DIRECTORY / 'steps.py']
    before = {p: p.read_bytes() for p in sources}
    subprocess.run([sys.executable, '-m', 'examples.purchase.acceptance', 'docs', '--check'], cwd=ROOT, check=True)
    assert {p: p.read_bytes() for p in sources} == before


def test_report_distinguishes_missing_skipped_and_stale():
    catalog = cases()
    digest = hashlib.sha256(json.dumps(program.spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    payload = {'schema_version': 1, 'implementation_sha256': 'impl', 'commit': 'example', 'working_tree_dirty': True, 'session_exitstatus': 0,
               'contract_sha256': digest, 'cases': [
                   {'case_id': catalog[0].id, 'status': 'passed', 'source_sha256': catalog[0].source_hash},
                   {'case_id': catalog[1].id, 'status': 'skipped', 'source_sha256': catalog[1].source_hash}]}
    text = render_report(payload, catalog, digest)
    assert '| 合格 |' in text
    assert '| スキップ |' in text
    assert '| 未実行 |' in text
    payload['contract_sha256'] = 'old'
    assert '過去結果（定義変更あり）：合格' in render_report(payload, catalog, digest)
    payload['cases'].append({'case_id': 'unknown', 'status': 'passed'})
    with pytest.raises(ValueError):
        render_report(payload, catalog, digest)


@pytest.mark.parametrize(('mutation', 'identity', 'assertion'), [
    ('early', 'scenario.purchase.schedule', 'application_status'),
    ('duplicate', 'scenario.purchase.schedule', 'order_count'),
    ('rejected-order', 'scenario.purchase.reject', 'order_count'),
    ('compensation', 'scenario.purchase.upload.final-failure', 'objects'),
])
def test_business_acceptance_detects_wrong_implementation(tmp_path, mutation, identity, assertion):
    report = tmp_path / 'report.json'
    result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/acceptance/test_purchase.py', '--acceptance-case', identity,
                             '--purchase-mutation', mutation, '--acceptance-report', str(report), '-q'],
                            cwd=ROOT, capture_output=True, text=True, timeout=40)
    assert result.returncode == 1, result.stdout + result.stderr
    payload = json.loads(report.read_text())
    entry = next(c for c in payload['cases'] if c['case_id'] == identity)
    assert entry['status'] == 'failed'
    assert 'AssertionError' in entry['failure']
    assert assertion in entry['failure']
    assert payload['summary']['failed'] == 1
    assert payload['summary']['not-run'] == 13


def test_clock_requires_timezone_and_cannot_move_backwards():
    from examples.purchase.acceptance.world import ManualClock
    from examples.purchase.scheduling import aware_time
    with pytest.raises(ValueError, match='timezone'):
        aware_time('2030-04-01T10:00:00')
    clock = ManualClock()
    with pytest.raises(ValueError, match='backwards'):
        clock.advance('2030-04-01T08:59:59+09:00')
    clock.advance('2030-04-01T00:00:00+00:00')
    assert clock.now().isoformat() == '2030-04-01T00:00:00+00:00'


def test_report_invalidates_changed_implementation():
    catalog = cases()
    digest = 'contract'
    payload = {'schema_version': 1, 'session_exitstatus': 0, 'contract_sha256': digest, 'implementation_sha256': 'old', 'cases': [
        {'case_id': catalog[0].id, 'status': 'passed', 'source_sha256': catalog[0].source_hash}]}
    assert '過去結果（定義変更あり）：合格' in render_report(payload, catalog, digest, 'new')


def test_unknown_case_filter_is_not_a_success(tmp_path):
    result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/acceptance', '--acceptance-case', 'scenario.unknown', '-q'],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert 'Unknown acceptance case IDs' in result.stderr + result.stdout
