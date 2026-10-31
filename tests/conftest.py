"""Purchase acceptance reporting; core unittest tests remain independent."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

pytest_plugins = ['examples.purchase.acceptance.steps']


def pytest_addoption(parser):
    parser.addoption('--acceptance-case', action='append', default=[], help='Run only these stable case IDs')
    parser.addoption('--acceptance-report', help='Write scenario results, including not-run cases, as JSON')
    parser.addoption('--purchase-mutation', choices=['early', 'duplicate', 'rejected-order', 'compensation'],
                     help='Deliberately break the purchase sample for mutation checks')


def pytest_configure(config):
    config.addinivalue_line('markers', 'acceptance_tag(tag): tag from the canonical purchase feature')
    config.addinivalue_line('markers', 'temporal: optional Temporal acceptance scenario')
    from examples.purchase.acceptance.catalog import cases
    catalog = cases()
    config.purchase_cases = {case.id: case for case in catalog}
    config.purchase_results = {case.id: {'case_id': case.id, 'scenario_id': case.scenario_id,
        'requirements': list(case.requirements), 'backend': 'temporal' if 'temporal' in case.tags else 'local',
        'source': case.uri, 'source_sha256': case.source_hash, 'status': 'not-run'} for case in catalog}


def pytest_bdd_apply_tag(tag, function):
    pytest.mark.acceptance_tag(tag)(function)
    return True


def case_id(item):
    tags = [m.args[0] for m in item.iter_markers('acceptance_tag')]
    ids = [tag for tag in tags if tag.startswith('scenario.')]
    if not ids:
        return None
    if len(set(ids)) != 1:
        raise ValueError(f'{item.nodeid}: ambiguous scenario IDs')
    example = getattr(item, 'callspec', None)
    values = example.params.get('_pytest_bdd_example', {}) if example else {}
    return ids[0] + ('.' + values['case'] if 'case' in values else '')


def pytest_collection_modifyitems(config, items):
    wanted = set(config.getoption('--acceptance-case'))
    if wanted - config.purchase_cases.keys():
        raise pytest.UsageError(f'Unknown acceptance case IDs: {sorted(wanted - config.purchase_cases.keys())}')
    removed = []
    for item in items:
        identity = case_id(item)
        if wanted and identity not in wanted:
            removed.append(item)
        if identity:
            if identity not in config.purchase_cases:
                raise ValueError(f'Collected scenario is not in canonical catalog: {identity}')
            item.purchase_case_id = identity
            if 'temporal' in config.purchase_cases[identity].tags:
                item.add_marker(pytest.mark.temporal)
            if 'temporal' in config.purchase_cases[identity].tags and os.environ.get('RUN_TEMPORAL_ACCEPTANCE') != '1':
                item.add_marker(pytest.mark.skip(reason='Set RUN_TEMPORAL_ACCEPTANCE=1 to run Temporal scenarios'))

    if removed:
        config.hook.pytest_deselected(items=removed)
        items[:] = [item for item in items if item not in removed]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    identity = getattr(item, 'purchase_case_id', None)
    if not identity:
        return
    entry = item.config.purchase_results[identity]
    if report.failed:
        entry.update(status='failed', failure=str(report.longrepr))
    elif report.skipped and entry['status'] != 'failed':
        entry.update(status='skipped', reason=str(report.longrepr))
    elif report.when == 'call' and report.passed and entry['status'] != 'failed':
        entry['status'] = 'passed'
    entry['nodeid'] = item.nodeid
    if report.when == 'teardown':
        entry['diagnostics'] = getattr(item, 'purchase_diagnostics', {})


def pytest_sessionfinish(session, exitstatus):
    destination = session.config.getoption('--acceptance-report')
    if not destination:
        return
    root = Path(__file__).resolve().parents[1]
    def git(*args):
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    from examples.purchase.contract import SPEC
    from examples.purchase.acceptance.catalog import implementation_hash
    from importlib.metadata import version
    import platform
    results = list(session.config.purchase_results.values())
    payload = {'commit': git('rev-parse', 'HEAD'), 'working_tree_dirty': bool(git('status', '--porcelain')),
               'contract_sha256': hashlib.sha256(json.dumps(SPEC, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
               'session_exitstatus': int(exitstatus), 'implementation_sha256': implementation_hash(),
               'runtime': {'python': platform.python_version(), 'pytest-bdd': version('pytest-bdd')},
               'options': {'mutation': session.config.getoption('--purchase-mutation'),
                           'temporal_enabled': os.environ.get('RUN_TEMPORAL_ACCEPTANCE') == '1'},
               'summary': {status: sum(e['status'] == status for e in results)
                           for status in ('passed', 'failed', 'skipped', 'not-run')}, 'cases': results}
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
