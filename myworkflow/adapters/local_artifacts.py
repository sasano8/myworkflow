"""Default artifact coordinator: short SQLite transactions in a temporary directory.

This is a local storage provider, not a transaction spanning application databases,
S3 or external APIs. Job IDs are database keys, never filesystem paths.
"""
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import tempfile

from myworkflow.adapters.sqlite import SQLiteDatabase
from myworkflow.blob_files import BlobRef
from myworkflow.artifact_jobs import (ArtifactConflict, ArtifactJob, ArtifactSnapshot, ArtifactWrite,
                                     InvalidJobState, JobConflict, JobState)


def _identity(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Artifact keys, namespaces and job IDs must be nonempty strings')


def _json_value(value):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _json_value(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _json_value(item)
        return
    raise ValueError('Artifacts must contain finite JSON values with string object keys')


def _request(writes):
    if not isinstance(writes, tuple) or not writes or any(not isinstance(w, ArtifactWrite) for w in writes):
        raise ValueError('Prepare requires a nonempty tuple of ArtifactWrite')
    for write in writes:
        _identity(write.key)
        if type(write.expected_version) is not int or write.expected_version < 0:
            raise ValueError('Expected versions must be nonnegative integers')
        if not isinstance(write.value, BlobRef):
            _json_value(write.value)
    if len({w.key for w in writes}) != len(writes):
        raise ValueError('An artifact can only be written once per request')
    records = []
    for write in sorted(writes, key=lambda w: w.key):
        record = {'key': write.key, 'value': asdict(write.value) if isinstance(write.value, BlobRef) else write.value,
                  'expected_version': write.expected_version}
        if isinstance(write.value, BlobRef):
            record['storage'] = 'file'
        records.append(record)
    return json.dumps(records, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':'))



class TemporaryArtifactCoordinator:
    """Instances/processes sharing root and namespace share prepared/committed jobs.

    The default location survives Python object/process lifetimes until the host
    removes its temporary files. Applications should choose a namespace; separate
    hosts/containers do not share this storage automatically.
    """
    def __init__(self, root: str | Path | None = None, *, namespace: str = 'default'):
        _identity(namespace)
        root = Path(root) if root is not None else Path(tempfile.gettempdir()) / 'myworkflow-artifacts'
        self.directory = root / hashlib.sha256(namespace.encode()).hexdigest()
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.database = SQLiteDatabase(self.directory / 'coordinator.sqlite')
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS artifacts(key TEXT PRIMARY KEY, value TEXT NOT NULL, version INTEGER NOT NULL)')
            if 'storage' not in {r[1] for r in db.execute('PRAGMA table_info(artifacts)')}:
                db.execute("ALTER TABLE artifacts ADD COLUMN storage TEXT NOT NULL DEFAULT 'json'")
            db.execute('CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, request TEXT NOT NULL, state TEXT NOT NULL, receipt TEXT NOT NULL)')

        from myworkflow.adapters.local_blob_files import LocalBlobStore
        self.blobs = LocalBlobStore(self.directory / 'jobs', self.database)

    @staticmethod
    def _job(row):
        identity, request, state, receipt = row
        return ArtifactJob(identity, JobState(state), tuple(w['key'] for w in json.loads(request)),
                           tuple((key, version) for key, version in json.loads(receipt)))

    def read(self, key: str) -> ArtifactSnapshot | None:
        _identity(key)
        with self.database.connect() as db:
            row = db.execute('SELECT value,version,storage FROM artifacts WHERE key=?', (key,)).fetchone()
        if row is None:
            return None
        value = json.loads(row[0])
        return ArtifactSnapshot(key, BlobRef(**value) if row[2] == 'file' else value, row[1])

    def status(self, job_id: str) -> ArtifactJob | None:
        _identity(job_id)
        with self.database.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        return self._job(row) if row else None

    def prepare(self, job_id: str, writes: tuple[ArtifactWrite, ...]) -> ArtifactJob:
        _identity(job_id)
        request = _request(writes)
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if previous:
                if previous[1] != request:
                    raise JobConflict(f'{job_id}: job ID is bound to different changes')
                return self._job(previous)
            for write in writes:
                if isinstance(write.value, BlobRef):
                    if write.value.job_id != job_id:
                        raise ValueError('A job can only publish its own staged files')
                    self.blobs._check_reference(db, write.value)
            db.execute('INSERT INTO jobs VALUES (?,?,?,?)', (job_id, request, JobState.PREPARED, '[]'))
            return self._job((job_id, request, JobState.PREPARED, '[]'))

    def commit(self, job_id: str) -> ArtifactJob:
        _identity(job_id)
        # Verify immutable file contents before taking the short publication transaction.
        with self.database.connect() as db:
            preview = db.execute('SELECT request,state FROM jobs WHERE id=?', (job_id,)).fetchone()
        if preview and preview[1] == JobState.PREPARED:
            for write in json.loads(preview[0]):
                if write.get('storage') == 'file':
                    self.blobs.verify(BlobRef(**write['value']))
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            job = self._job(row)
            if job.state == JobState.COMMITTED:
                return job
            if job.state != JobState.PREPARED:
                raise InvalidJobState(f'{job_id}: discarded job cannot commit')
            writes = json.loads(row[1])
            # Validate every expected version before applying any writes.
            for write in writes:
                if write.get('storage') == 'file':
                    self.blobs._check_reference(db, BlobRef(**write['value']))
                existing = db.execute('SELECT version FROM artifacts WHERE key=?', (write['key'],)).fetchone()
                actual = existing[0] if existing else 0
                if actual != write['expected_version']:
                    raise ArtifactConflict(f"{job_id}/{write['key']}: expected {write['expected_version']}, got {actual}")
            versions = []
            for write in writes:
                version = write['expected_version'] + 1
                db.execute('INSERT INTO artifacts(key,value,version,storage) VALUES (?,?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,version=excluded.version,storage=excluded.storage',
                           (write['key'], json.dumps(write['value'], ensure_ascii=False, allow_nan=False), version, write.get('storage', 'json')))
                versions.append((write['key'], version))
            receipt = json.dumps(versions)
            db.execute('UPDATE jobs SET state=?,receipt=? WHERE id=?', (JobState.COMMITTED, receipt, job_id))
            return self._job((job_id, row[1], JobState.COMMITTED, receipt))

    def discard(self, job_id: str) -> ArtifactJob:
        _identity(job_id)
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row is None:
                if not self.blobs._job_directory(job_id).exists():
                    raise KeyError(job_id)
                row = (job_id, '[]', JobState.DISCARDED, '[]')
                db.execute('INSERT INTO jobs VALUES (?,?,?,?)', row)
            job = self._job(row)
            if job.state == JobState.COMMITTED:
                raise InvalidJobState(f'{job_id}: committed job cannot discard')
            db.execute('UPDATE jobs SET state=? WHERE id=?', (JobState.DISCARDED, job_id))
            result = self._job((job_id, row[1], JobState.DISCARDED, row[3]))
        self.blobs._discard(job_id)
        return result
