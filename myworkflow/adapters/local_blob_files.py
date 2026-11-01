"""Stream blobs into immutable job-owned files; SQLite contains references only."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

from myworkflow.storage.artifacts import InvalidJobState, JobConflict, JobState
from myworkflow.storage.blobs import BlobRef

CHUNK_SIZE = 1024 * 1024


class LocalBlobStore:
    def __init__(self, directory, database):
        self.directory, self.database = Path(directory), database
        with self.database.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS blob_files(job_id TEXT, name TEXT, sha256 TEXT NOT NULL, size INTEGER NOT NULL, PRIMARY KEY(job_id,name))')

    def _job_directory(self, job_id):
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError('Blob job ID must be a nonempty string')
        return self.directory / hashlib.sha256(job_id.encode()).hexdigest()

    def path(self, reference):
        """Local diagnostic path; callers use open() to read through the provider."""
        return self._job_directory(reference.job_id) / (hashlib.sha256(reference.name.encode()).hexdigest() + '-' + reference.sha256)

    @staticmethod
    def _check_reference(db, reference):
        if not isinstance(reference, BlobRef):
            raise ValueError('Expected BlobRef')
        row = db.execute('SELECT sha256,size FROM blob_files WHERE job_id=? AND name=?', (reference.job_id, reference.name)).fetchone()
        if row != (reference.sha256, reference.size):
            raise ValueError('Blob reference does not match the stored file metadata')
        job = db.execute('SELECT state FROM jobs WHERE id=?', (reference.job_id,)).fetchone()
        if job and job[0] == JobState.DISCARDED:
            raise InvalidJobState('Discarded job files cannot be read or committed')

    def stage_file(self, job_id, name, source):
        with Path(source).open('rb') as stream:
            return self.stage_stream(job_id, name, stream)

    def stage_stream(self, job_id, name, source):
        folder = self._job_directory(job_id)
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Blob name must be a nonempty string')
        with self.database.connect() as db:
            job = db.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
            existing = db.execute('SELECT 1 FROM blob_files WHERE job_id=? AND name=?', (job_id, name)).fetchone()
        if job and (job[0] == JobState.DISCARDED or not existing):
            raise InvalidJobState('The job cannot stage a new file')
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = None
        try:
            digest, size = hashlib.sha256(), 0
            with tempfile.NamedTemporaryFile(dir=folder, prefix='.upload-', delete=False) as target:
                temporary = Path(target.name)
                while True:
                    chunk = source.read(CHUNK_SIZE)
                    if not isinstance(chunk, bytes):
                        raise TypeError('Blob source must be a binary stream')
                    if not chunk:
                        break
                    target.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                target.flush()
                os.fsync(target.fileno())
            reference = BlobRef(job_id, name, digest.hexdigest(), size)
            with self.database.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                job = db.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
                existing = db.execute('SELECT sha256,size FROM blob_files WHERE job_id=? AND name=?', (job_id, name)).fetchone()
                if job and job[0] == JobState.DISCARDED:
                    raise InvalidJobState('Discarded jobs cannot stage files')
                if existing:
                    if existing != (reference.sha256, reference.size):
                        raise JobConflict(f'{job_id}/{name}: file name is bound to different content')
                    if not self.path(reference).is_file():
                        raise FileNotFoundError(self.path(reference))
                    return reference
                if job:
                    raise InvalidJobState('A prepared or committed request cannot add files')
                os.chmod(temporary, 0o400)
                os.replace(temporary, self.path(reference))
                db.execute('INSERT INTO blob_files VALUES (?,?,?,?)', (job_id, name, reference.sha256, reference.size))
            return reference
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def list_files(self, job_id):
        self._job_directory(job_id)  # validate the logical ID
        with self.database.connect() as db:
            rows = db.execute('SELECT name,sha256,size FROM blob_files WHERE job_id=? ORDER BY name', (job_id,)).fetchall()
        return tuple(BlobRef(job_id, name, digest, size) for name, digest, size in rows)

    @contextmanager
    def open(self, reference):
        with self.database.connect() as db:
            self._check_reference(db, reference)
        with self.path(reference).open('rb') as stream:
            if os.fstat(stream.fileno()).st_size != reference.size:
                raise ValueError('Blob size does not match its reference')
            yield stream

    def verify(self, reference):
        digest = hashlib.sha256()
        with self.open(reference) as source:
            while chunk := source.read(CHUNK_SIZE):
                digest.update(chunk)
        if digest.hexdigest() != reference.sha256:
            raise ValueError('Blob checksum does not match its reference')

    def _discard(self, job_id):
        # The coordinator has durably marked the job discarded before removing files.
        folder = self._job_directory(job_id)
        if folder.exists():
            shutil.rmtree(folder)
        with self.database.connect() as db:
            db.execute('DELETE FROM blob_files WHERE job_id=?', (job_id,))
