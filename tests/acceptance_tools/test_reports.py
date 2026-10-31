"""Result-state reducer tests use synthetic probes, not business acceptance evidence."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from myworkflow.acceptance.reports import validate_report
from myworkflow.fingerprints import tree_fingerprint

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(('mode', 'status', 'exitcode'), [
    ('setup', 'failed', 1), ('teardown', 'failed', 1), ('skip', 'skipped', 0),
    ('unselected', 'not-run', 5), ('collection', 'not-run', 2),
])
def test_result_states_do_not_claim_success_on_failed_or_unrun_probe(tmp_path, mode, status, exitcode):
    probe = tmp_path / 'test_probe.py'
    body = '''import pytest
@pytest.fixture(autouse=True)
def lifecycle():
    if MODE == 'setup': raise ValueError('setup failure')
    yield
    if MODE == 'teardown': raise ValueError('teardown failure')
@pytest.mark.acceptance_tag('scenario.tickets.issue')
def test_probe():
    if MODE == 'skip': pytest.skip('not executed')
'''
    probe.write_text('invalid syntax !' if mode == 'collection' else f'MODE={mode!r}\n' + body)
    report = tmp_path / 'result.json'
    args = [sys.executable, '-m', 'pytest', '-p', 'myworkflow.pytest_plugin', str(probe),
            '--acceptance-config', 'examples.tickets.acceptance.catalog', '--acceptance-report', str(report), '-q']
    if mode == 'unselected': args += ['-k', 'absent']
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == exitcode, result.stdout + result.stderr
    payload = json.loads(report.read_text())
    validate_report(payload)
    assert payload['cases'][0]['status'] == status
    assert payload['summary']['passed'] == 0
    assert payload['session_exitstatus'] == exitcode


def test_report_schema_rejects_duplicate_ids_invalid_states_and_missing_versions():
    payload = {'schema_version': 1, 'session_exitstatus': 0, 'contract_sha256': 'a', 'implementation_sha256': 'b',
               'cases': [{'case_id': 'one', 'status': 'passed', 'source_sha256': 'c'}]}
    validate_report(payload)
    invalid = [[], {**payload, 'schema_version': 2}, {**payload, 'schema_version': True}, {**payload, 'cases': [*payload['cases'], *payload['cases']]},
               {**payload, 'cases': [{'case_id': 'one', 'status': 'unknown'}]},
               {**payload, 'cases': [{'case_id': 'one', 'status': 'passed'}]},
               {**payload, 'cases': [None]}]
    for value in invalid:
        with pytest.raises(ValueError): validate_report(value)


def test_fingerprint_discovers_new_sources_but_excludes_generated_markdown(tmp_path):
    source = tmp_path / 'src'; source.mkdir()
    (source / 'a.py').write_text('a=1')
    before = tree_fingerprint(tmp_path, [source])
    (source / 'notes.md').write_text('generated')
    assert tree_fingerprint(tmp_path, [source]) == before
    (source / 'new_adapter.py').write_text('b=2')
    assert tree_fingerprint(tmp_path, [source]) != before
