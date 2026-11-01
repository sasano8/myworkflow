"""Blob bytes stay in streamed job-owned files, while commits publish references."""
from contextlib import closing
from dataclasses import replace
import hashlib
import io
import json
import sqlite3
import subprocess
import sys

import pytest

from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.artifact_jobs import ArtifactWrite, InvalidJobState, JobConflict, JobState
from myworkflow.blob_files import BlobRef, BlobStore


@pytest.fixture
def coordinator(tmp_path):
    return TemporaryArtifactCoordinator(tmp_path, namespace='files')


def test_file_is_job_owned_and_database_only_contains_metadata(coordinator, tmp_path):
    source = tmp_path / 'source.pdf'
    content = b'%PDF-blob-content\x00\xff'
    source.write_bytes(content)
    ref = coordinator.blobs.stage_file('job/../one', '../../attachment.pdf', source)
    assert isinstance(coordinator.blobs, BlobStore)
    assert ref.sha256 == hashlib.sha256(content).hexdigest()
    assert ref.size == len(content)
    assert coordinator.blobs.path(ref).is_relative_to(coordinator.directory / 'jobs')
    assert source.read_bytes() == content
    coordinator.prepare(ref.job_id, (ArtifactWrite('attachment', ref), ArtifactWrite('state', 'ready')))
    assert coordinator.read('attachment') is None
    coordinator.commit(ref.job_id)
    assert coordinator.read('attachment').value == ref
    with coordinator.blobs.open(ref) as stream:
        assert stream.read() == content
    with coordinator.database.connect() as db:
        stored, storage = db.execute("SELECT value,storage FROM artifacts WHERE key='attachment'").fetchone()
        assert storage == 'file'
        assert json.loads(stored) == {'job_id': ref.job_id, 'name': ref.name, 'sha256': ref.sha256, 'size': ref.size}
        assert 'blob-content' not in stored
        assert db.execute('SELECT sha256,size FROM blob_files').fetchone() == (ref.sha256, ref.size)


def test_large_stream_is_read_in_chunks_and_does_not_expand_sqlite(coordinator):
    class Chunks:
        remaining = 5 * 1024 * 1024
        calls = []
        def read(self, size):
            self.calls.append(size)
            assert 0 < size <= 1024 * 1024
            count = min(size, self.remaining)
            self.remaining -= count
            return b'x' * count
    stream = Chunks()
    ref = coordinator.blobs.stage_stream('large', 'data.bin', stream)
    coordinator.prepare('large', (ArtifactWrite('data', ref),))
    coordinator.commit('large')
    assert ref.size == 5 * 1024 * 1024
    assert len(stream.calls) == 6
    assert coordinator.blobs.path(ref).stat().st_size == ref.size
    assert coordinator.directory.joinpath('coordinator.sqlite').stat().st_size < 100 * 1024


def test_repeated_stage_and_commit_do_not_create_duplicate_files(coordinator):
    first = coordinator.blobs.stage_stream('job', 'data', io.BytesIO(b'content'))
    assert coordinator.blobs.stage_stream('job', 'data', io.BytesIO(b'content')) == first
    with pytest.raises(JobConflict):
        coordinator.blobs.stage_stream('job', 'data', io.BytesIO(b'different'))
    coordinator.prepare('job', (ArtifactWrite('file', first),))
    with pytest.raises(InvalidJobState):
        coordinator.blobs.stage_stream('job', 'another', io.BytesIO(b'late'))
    committed = coordinator.commit('job')
    assert coordinator.commit('job') == committed
    assert coordinator.blobs.stage_stream('job', 'data', io.BytesIO(b'content')) == first
    assert len(list(coordinator.blobs.path(first).parent.iterdir())) == 1


def test_discard_removes_only_its_job_files_and_preserves_committed_files(coordinator):
    first = coordinator.blobs.stage_stream('first', 'file', io.BytesIO(b'same'))
    second = coordinator.blobs.stage_stream('second', 'file', io.BytesIO(b'same'))
    coordinator.prepare('first', (ArtifactWrite('file', first),))
    coordinator.commit('first')
    coordinator.prepare('second', (ArtifactWrite('file', second, expected_version=1),))
    coordinator.discard('second')
    assert not coordinator.blobs.path(second).exists()
    assert coordinator.blobs.path(first).exists()
    assert coordinator.read('file').value == first
    with pytest.raises(InvalidJobState):
        coordinator.discard('first')
    with pytest.raises(InvalidJobState):
        coordinator.blobs.stage_stream('second', 'file', io.BytesIO(b'same'))
    assert coordinator.discard('second').state == JobState.DISCARDED


def test_files_can_be_discarded_before_artifact_prepare(coordinator):
    ref = coordinator.blobs.stage_stream('draft', 'file', io.BytesIO(b'draft'))
    assert coordinator.status('draft') is None
    coordinator.discard('draft')
    assert coordinator.status('draft').state == JobState.DISCARDED
    assert coordinator.blobs.list_files('draft') == ()
    assert not coordinator.blobs.path(ref).exists()


def test_another_job_cannot_publish_a_file_it_does_not_own(coordinator):
    ref = coordinator.blobs.stage_stream('owner', 'file', io.BytesIO(b'owned'))
    with pytest.raises(ValueError, match='own staged files'):
        coordinator.prepare('other', (ArtifactWrite('file', ref),))
    assert coordinator.status('other') is None
    with pytest.raises(ValueError, match='metadata'):
        coordinator.blobs.verify(replace(ref, sha256='0' * 64))


@pytest.mark.parametrize('damage', ['missing', 'corrupt'])
def test_unavailable_file_prevents_publication_of_data_and_state(coordinator, damage):
    ref = coordinator.blobs.stage_stream('job', 'file', io.BytesIO(b'original'))
    coordinator.prepare('job', (ArtifactWrite('file', ref), ArtifactWrite('state', 'ready')))
    path = coordinator.blobs.path(ref)
    if damage == 'missing':
        path.unlink()
    else:
        path.chmod(0o600)
        path.write_bytes(b'modified')
    with pytest.raises((ValueError, FileNotFoundError)):
        coordinator.commit('job')
    assert coordinator.status('job').state == JobState.PREPARED
    assert coordinator.read('file') is None
    assert coordinator.read('state') is None


def test_publishing_failure_retains_files_for_retry(coordinator):
    ref = coordinator.blobs.stage_stream('job', 'file', io.BytesIO(b'original'))
    coordinator.prepare('job', (ArtifactWrite('file', ref), ArtifactWrite('z-state', 'ready')))
    with coordinator.database.connect() as db:
        db.execute("CREATE TRIGGER fail_state BEFORE INSERT ON artifacts WHEN NEW.key='z-state' BEGIN SELECT RAISE(ABORT,'fault'); END")
    with pytest.raises(sqlite3.IntegrityError):
        coordinator.commit('job')
    assert coordinator.read('file') is None
    assert coordinator.blobs.path(ref).exists()
    with coordinator.database.connect() as db:
        db.execute('DROP TRIGGER fail_state')
    coordinator.commit('job')
    assert coordinator.read('file').value == ref


def test_interrupted_stream_does_not_register_a_partial_blob(coordinator):
    class BrokenStream:
        def read(self, size):
            raise OSError('disconnected')
    with pytest.raises(OSError):
        coordinator.blobs.stage_stream('broken', 'file', BrokenStream())
    assert coordinator.blobs.list_files('broken') == ()
    assert coordinator.status('broken') is None
    coordinator.discard('broken')
    assert not coordinator.blobs._job_directory('broken').exists()


def test_reference_and_file_survive_process_restart(coordinator, tmp_path):
    ref = coordinator.blobs.stage_stream('job', 'file', io.BytesIO(b'persistent'))
    coordinator.prepare('job', (ArtifactWrite('file', ref),))
    script = "from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator; import sys; c=TemporaryArtifactCoordinator(sys.argv[1],namespace='files'); c.commit('job'); r=c.read('file').value; c.blobs.verify(r)"
    subprocess.run([sys.executable, '-c', script, str(tmp_path)], check=True)
    assert coordinator.read('file').value == ref
    assert coordinator.status('job').state == JobState.COMMITTED


def test_old_json_artifacts_are_preserved_when_storage_column_is_added(tmp_path):
    # A local provider created before file support has only three artifact columns.
    coordinator = TemporaryArtifactCoordinator(tmp_path, namespace='upgrade')
    with coordinator.database.connect() as db:
        db.execute('DROP TABLE artifacts')
        db.execute('CREATE TABLE artifacts(key TEXT PRIMARY KEY,value TEXT NOT NULL,version INTEGER NOT NULL)')
        db.execute('INSERT INTO artifacts VALUES (?,?,?)', ('business', '{"amount":100}', 1))
    reopened = TemporaryArtifactCoordinator(tmp_path, namespace='upgrade')
    assert reopened.read('business').value == {'amount': 100}
    reopened.prepare('update', (ArtifactWrite('business', {'amount': 200}, expected_version=1),))
    reopened.commit('update')
    assert reopened.read('business').version == 2


def test_purchase_sample_stores_bodies_in_files_and_compensation_removes_them(tmp_path):
    from examples.purchase.services import Services
    services = Services(tmp_path / 'purchase.db')
    services.begin('upload')
    key = services.put('upload', 'A', '本文はファイルだけに保存')
    with services.connect() as db:
        owner, version, digest = db.execute('SELECT owner,version,sha256 FROM objects WHERE key=?', (key,)).fetchone()
        assert 'body' not in {row[1] for row in db.execute('PRAGMA table_info(objects)')}
    path = services.objects.inner.path(key, version)
    assert path.read_text() == '本文はファイルだけに保存'
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    services.delete('upload', 'A')
    assert not path.exists()
    assert owner == 'upload'


def test_purchase_sample_refuses_to_remove_files_with_changed_owner(tmp_path):
    from examples.purchase.services import Services
    services = Services(tmp_path / 'purchase.db')
    services.begin('upload')
    key = services.put('upload', 'A', 'original')
    with services.connect() as db:
        version = db.execute('SELECT version FROM objects WHERE key=?', (key,)).fetchone()[0]
        db.execute("UPDATE objects SET owner='other',version='other-version'")
    path = services.objects.inner.path(key, version)
    with pytest.raises(ValueError, match='another execution'):
        services.delete('upload', 'A')
    assert path.read_text() == 'original'


def test_legacy_purchase_body_is_never_silently_deleted(tmp_path):
    from examples.purchase.services import Services
    path = tmp_path / 'old.db'
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('CREATE TABLE objects(key TEXT PRIMARY KEY,owner TEXT,version TEXT,body TEXT)')
        db.execute('INSERT INTO objects VALUES (?,?,?,?)', ('key', 'owner', 'version', 'preserve me'))
    with pytest.raises(ValueError, match='explicit export'):
        Services(path)
    with closing(sqlite3.connect(path)) as db, db:
        assert db.execute('SELECT body FROM objects').fetchone()[0] == 'preserve me'
