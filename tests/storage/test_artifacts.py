"""Provider contracts: durable preparation, idempotent commit and atomic data/state updates."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import subprocess
import sys

import pytest

from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.storage.artifacts import (ArtifactConflict, ArtifactCoordinator, ArtifactWrite,
                                     InvalidJobState, JobConflict, JobState)


@pytest.fixture
def coordinator(tmp_path):
    return TemporaryArtifactCoordinator(tmp_path, namespace='tests')


def test_prepare_is_private_until_commit_and_receipt_survives_reopen(coordinator, tmp_path):
    changes = (ArtifactWrite('application:x', {'owner': 'alice'}), ArtifactWrite('state:x', 'pending'))
    staged = coordinator.prepare('job/../1', changes)
    assert isinstance(coordinator, ArtifactCoordinator)
    assert staged.state == JobState.PREPARED
    assert coordinator.read('application:x') is None
    reopened = TemporaryArtifactCoordinator(tmp_path, namespace='tests')
    assert reopened.status('job/../1') == staged
    receipt = reopened.commit('job/../1')
    assert receipt.state == JobState.COMMITTED
    assert reopened.read('application:x').value == {'owner': 'alice'}
    assert reopened.read('state:x').value == 'pending'
    assert coordinator.commit('job/../1') == receipt
    assert coordinator.prepare('job/../1', tuple(reversed(changes))) == receipt
    assert coordinator.read('state:x').version == 1
    with pytest.raises(JobConflict):
        coordinator.prepare('job/../1', (ArtifactWrite('state:x', 'other'),))


def test_request_and_read_results_do_not_share_mutable_values(coordinator):
    value = {'items': ['original']}
    coordinator.prepare('job', (ArtifactWrite('a', value),))
    value['items'].append('changed')
    coordinator.commit('job')
    snapshot = coordinator.read('a')
    assert snapshot.value == {'items': ['original']}
    snapshot.value['items'].clear()
    assert coordinator.read('a').value == {'items': ['original']}


def test_conflict_does_not_publish_other_artifacts(coordinator):
    coordinator.prepare('first', (ArtifactWrite('a', 1),))
    coordinator.prepare('second', (ArtifactWrite('a', 2), ArtifactWrite('b', 2)))
    coordinator.commit('first')
    with pytest.raises(ArtifactConflict):
        coordinator.commit('second')
    assert coordinator.read('a').value == 1
    assert coordinator.read('b') is None
    assert coordinator.status('second').state == JobState.PREPARED


def test_receipt_is_stable_even_after_a_new_job_updates_the_artifact(coordinator):
    coordinator.prepare('first', (ArtifactWrite('a', 1),))
    first = coordinator.commit('first')
    coordinator.prepare('update', (ArtifactWrite('a', 2, expected_version=1),))
    assert coordinator.commit('update').versions == (('a', 2),)
    assert coordinator.commit('first') == first
    assert coordinator.read('a').value == 2
    assert coordinator.read('a').version == 2


def test_discard_is_idempotent_and_committed_data_cannot_discard(coordinator):
    changes = (ArtifactWrite('a', 1),)
    coordinator.prepare('discard', changes)
    receipt = coordinator.discard('discard')
    assert receipt.state == JobState.DISCARDED
    assert coordinator.discard('discard') == receipt
    assert coordinator.prepare('discard', changes) == receipt
    with pytest.raises(InvalidJobState):
        coordinator.commit('discard')
    coordinator.prepare('success', changes)
    coordinator.commit('success')
    with pytest.raises(InvalidJobState):
        coordinator.discard('success')


def test_database_failure_rolls_back_all_artifacts_and_receipt(coordinator):
    coordinator.prepare('job', (ArtifactWrite('a', 'data'), ArtifactWrite('z-state', 'approved')))
    with coordinator.database.connect() as db:
        db.execute("CREATE TRIGGER fail_state BEFORE INSERT ON artifacts WHEN NEW.key='z-state' BEGIN SELECT RAISE(ABORT, 'disk fault'); END")
    with pytest.raises(sqlite3.IntegrityError, match='disk fault'):
        coordinator.commit('job')
    assert coordinator.read('a') is None
    assert coordinator.read('z-state') is None
    assert coordinator.status('job').state == JobState.PREPARED
    with coordinator.database.connect() as db:
        db.execute('DROP TRIGGER fail_state')
    assert coordinator.commit('job').state == JobState.COMMITTED


def test_two_instances_competing_for_one_version_have_one_winner(coordinator, tmp_path):
    coordinator.prepare('one', (ArtifactWrite('a', 'one'),))
    coordinator.prepare('two', (ArtifactWrite('a', 'two'),))
    def commit(job):
        other = TemporaryArtifactCoordinator(tmp_path, namespace='tests')
        try:
            return other.commit(job).state
        except ArtifactConflict:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(commit, ('one', 'two')))
    assert outcomes.count(JobState.COMMITTED) == 1
    assert outcomes.count('conflict') == 1
    assert coordinator.read('a').version == 1


def test_preparation_survives_process_exit_and_another_process_can_commit(coordinator, tmp_path):
    script = '''import sys
from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.storage.artifacts import ArtifactWrite
store = TemporaryArtifactCoordinator(sys.argv[1], namespace='tests')
store.prepare('child', (ArtifactWrite('a', {'from': 'child'}),))
'''
    subprocess.run([sys.executable, '-c', script, str(tmp_path)], check=True)
    assert coordinator.status('child').state == JobState.PREPARED
    subprocess.run([sys.executable, '-c', "from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator; import sys; TemporaryArtifactCoordinator(sys.argv[1], namespace='tests').commit('child')", str(tmp_path)], check=True)
    assert coordinator.status('child').state == JobState.COMMITTED
    assert coordinator.read('a').value == {'from': 'child'}


def test_default_temporary_location_is_shared_and_namespaces_are_isolated(tmp_path, monkeypatch):
    monkeypatch.setattr('myworkflow.adapters.local_artifacts.tempfile.gettempdir', lambda: str(tmp_path))
    first = TemporaryArtifactCoordinator(namespace='one')
    first.prepare('job', (ArtifactWrite('a', 1),))
    other = TemporaryArtifactCoordinator(namespace='one')
    assert other.directory.is_relative_to(tmp_path)
    assert other.status('job').state == JobState.PREPARED
    isolated = TemporaryArtifactCoordinator(namespace='two')
    assert isolated.status('job') is None


@pytest.mark.parametrize('writes', [(), [ArtifactWrite('a', 1)], (ArtifactWrite('', 1),),
    (ArtifactWrite('a', 1), ArtifactWrite('a', 2)), (ArtifactWrite('a', 1, True),),
    (ArtifactWrite('a', float('nan')),), (ArtifactWrite('a', {1: 'not a JSON key'}),),
    (ArtifactWrite('a', object()),), (ArtifactWrite('a', ('tuple',)),)])
def test_invalid_preparations_do_not_create_a_job(coordinator, writes):
    with pytest.raises(ValueError):
        coordinator.prepare('invalid', writes)
    assert coordinator.status('invalid') is None


def test_unknown_jobs_and_invalid_ids_are_explicit(coordinator):
    assert coordinator.status('missing') is None
    with pytest.raises(KeyError):
        coordinator.commit('missing')
    with pytest.raises(KeyError):
        coordinator.discard('missing')
    with pytest.raises(ValueError):
        coordinator.status(' ')


def test_pipeline_stages_then_commits_data_and_business_state(coordinator, tmp_path):
    from examples.feature_demos.prepared_approval.application import engine, reviewer, seed
    from myworkflow.executable import Principal
    seed(coordinator)
    result = engine(coordinator, tmp_path / 'runs.db').invoke('b.staged_approve', 't.staged_approve',
        {'id': 'example'}, Principal('bob', frozenset({reviewer.id})), run_id='approval')
    assert result.code == 0
    assert coordinator.status('approval').state == JobState.COMMITTED
    assert coordinator.read('application:example').value['approved_by'] == 'bob'
    assert coordinator.read('state:example').value == 'state.staged_approved'


def test_pipeline_stop_before_commit_keeps_preparation_for_explicit_recovery(coordinator, tmp_path):
    from examples.feature_demos.prepared_approval.application import engine, reviewer, seed
    from myworkflow.executable import Principal
    seed(coordinator)
    class StopBeforeCommit:
        def __getattr__(self, name):
            return getattr(coordinator, name)
        def commit(self, job_id):
            raise RuntimeError('worker stopped before commit')
    result = engine(StopBeforeCommit(), tmp_path / 'runs.db').invoke('b.staged_approve', 't.staged_approve',
        {'id': 'example'}, Principal('bob', frozenset({reviewer.id})), run_id='approval')
    assert result.code == 1
    assert coordinator.status('approval').state == JobState.PREPARED
    assert coordinator.read('state:example').value == 'state.staged_pending'
    assert 'approved_by' not in coordinator.read('application:example').value
    reopened = TemporaryArtifactCoordinator(tmp_path, namespace='tests')
    reopened.commit('approval')
    assert reopened.read('state:example').value == 'state.staged_approved'


def test_pipeline_rejection_does_not_prepare_or_change_artifacts(coordinator, tmp_path):
    from examples.feature_demos.prepared_approval.application import engine, reviewer, seed
    from myworkflow.executable import Principal
    seed(coordinator)
    result = engine(coordinator, tmp_path / 'runs.db').invoke('b.staged_approve', 't.staged_approve',
        {'id': 'example'}, Principal('alice', frozenset({reviewer.id})), run_id='self-approval')
    assert result.code == 11
    assert coordinator.status('self-approval') is None
    assert coordinator.read('state:example').value == 'state.staged_pending'
