"""Opt-in, application-configured acceptance collection and result recording."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest



def pytest_addoption(parser):
    parser.addoption('--acceptance-case', action='append', default=[], help='Run only these stable case IDs')
    parser.addoption('--acceptance-report', help='Write scenario results, including not-run cases, as JSON')
    parser.addoption('--acceptance-config', action='append', default=[], help='Module exporting an AcceptanceConfig named CONFIG')
    parser.addoption('--acceptance-fault', '--purchase-mutation', dest='acceptance_fault', help='Application-specific test fault')


def pytest_configure(config):
    config.addinivalue_line('markers', 'acceptance_tag(tag): tag from the configured canonical feature')
    config.addinivalue_line('markers', 'temporal: optional Temporal acceptance scenario')
    config.addinivalue_line('markers', 'acceptance_config(module): application acceptance configuration')
    config.acceptance_cases = {}
    config.acceptance_results = {}
    config.acceptance_apps = {}
    config.acceptance_fingerprints = {}
    _load_apps(config, set(config.getoption("--acceptance-config")))


@pytest.hookimpl(optionalhook=True)
def pytest_bdd_apply_tag(tag, function):
    pytest.mark.acceptance_tag(tag)(function)
    return True


from myworkflow.acceptance.pytest_bridge import case_id


def pytest_collection_modifyitems(config, items):
    modules = set(config.getoption('--acceptance-config'))
    modules.update(m.args[0] for item in items for m in item.iter_markers('acceptance_config'))
    _load_apps(config, modules)
    wanted = set(config.getoption('--acceptance-case'))
    if wanted - config.acceptance_cases.keys():
        raise pytest.UsageError(f'Unknown acceptance case IDs: {sorted(wanted - config.acceptance_cases.keys())}')
    removed = []
    for item in items:
        identity = case_id(item)
        if wanted and identity not in wanted:
            removed.append(item)
        if identity:
            if identity not in config.acceptance_cases:
                raise ValueError(f'Collected scenario is not in canonical catalog: {identity}')
            item.acceptance_case_id = identity
            app = config.acceptance_apps[config.acceptance_results[identity]['application']]
            for tag, variable in app.capabilities:
                if tag in config.acceptance_cases[identity].tags:
                    item.add_marker(getattr(pytest.mark, tag))
                    if os.environ.get(variable) != '1':
                        item.add_marker(pytest.mark.skip(reason=f'Set {variable}=1 to enable {tag}'))

    if removed:
        config.hook.pytest_deselected(items=removed)
        items[:] = [item for item in items if item not in removed]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    identity = getattr(item, 'acceptance_case_id', None)
    if not identity:
        return
    entry = item.config.acceptance_results[identity]
    if report.failed:
        entry.update(status='failed', failure=str(report.longrepr))
    elif report.skipped and entry['status'] != 'failed':
        entry.update(status='skipped', reason=str(report.longrepr))
    elif report.when == 'call' and report.passed and entry['status'] != 'failed':
        entry['status'] = 'passed'
    entry['nodeid'] = item.nodeid
    if report.when == 'teardown':
        entry['diagnostics'] = getattr(item, 'acceptance_diagnostics', {})


def pytest_sessionfinish(session, exitstatus):
    destination = session.config.getoption('--acceptance-report')
    if not destination:
        return
    apps = session.config.acceptance_apps
    roots = {app.root for app in apps.values()}
    root = next(iter(roots)) if len(roots) == 1 else Path(session.config.rootpath)
    def git(*args):
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    import platform
    from importlib.metadata import version, PackageNotFoundError
    apps = session.config.acceptance_apps
    results = list(session.config.acceptance_results.values())
    for entry in results:
        contract, implementation = session.config.acceptance_fingerprints[entry['application']]
        entry['contract_sha256'] = contract
        entry['implementation_sha256'] = implementation
    contracts = {name: session.config.acceptance_fingerprints[name][0] for name in apps}
    implementations = {name: session.config.acceptance_fingerprints[name][1] for name in apps}
    def aggregate(values):
        return next(iter(values.values())) if len(values) == 1 else hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
    try:
        bdd_version = version('pytest-bdd')
    except PackageNotFoundError:
        bdd_version = None
    payload = {'schema_version': 1, 'commit': git('rev-parse', 'HEAD'), 'working_tree_dirty': bool(git('status', '--porcelain')),
               'session_exitstatus': int(exitstatus), 'contract_sha256': aggregate(contracts),
               'implementation_sha256': aggregate(implementations),
               'runtime': {'python': platform.python_version(), 'pytest-bdd': bdd_version},
               'options': {'mutation': session.config.getoption('acceptance_fault')},
               'summary': {status: sum(e['status'] == status for e in results) for status in ('passed', 'failed', 'skipped', 'not-run')},
               'cases': results}
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _load_apps(config, modules):
    import importlib
    for module in sorted(modules):
        if module in config.acceptance_apps:
            continue
        app = importlib.import_module(module).CONFIG
        config.acceptance_apps[module] = app
        config.acceptance_fingerprints[module] = (app.contract_hash(), app.implementation_hash())
        for case in app.cases():
            if case.id in config.acceptance_cases:
                raise pytest.UsageError(f'Duplicate configured case ID: {case.id}')
            config.acceptance_cases[case.id] = case
            config.acceptance_results[case.id] = {'case_id': case.id, 'scenario_id': case.scenario_id,
                'requirements': list(case.requirements), 'source': case.uri, 'source_sha256': case.source_hash,
                'application': module, 'status': 'not-run'}
