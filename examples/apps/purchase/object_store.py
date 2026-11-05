"""File-backed object/intent model. SQLite keeps ownership/digests, never blob bodies."""

import hashlib
import os
from pathlib import Path
import tempfile
from uuid import uuid4


class FileObjectStore:
    def __init__(self, database):
        self.database = database
        self.directory = Path(database.path + ".objects")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)

    def connect(self):
        return self.database.connect()

    def path(self, key, version):
        # The intent's unique version keeps compensation away from replacement files.
        job_key, slot = key.rsplit("/", 1)
        return (
            self.directory
            / hashlib.sha256(job_key.encode()).hexdigest()
            / hashlib.sha256(slot.encode()).hexdigest()
            / hashlib.sha256(version.encode()).hexdigest()
        )

    def prepare(self, run_id, slot):
        key = f"purchase/{run_id}/{slot}"
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO intents VALUES (?,?,?,?,?)",
                (run_id, slot, key, str(uuid4()), "pending"),
            )
            intent = db.execute(
                "SELECT key,version,state FROM intents WHERE run_id=? AND slot=?",
                (run_id, slot),
            ).fetchone()
            if intent[2] == "compensated":
                raise ValueError("Compensated run cannot be reused")
        return key, intent[1]

    def put(self, run_id, slot, body):
        # This sample's request type is text. The framework's BlobStore accepts streams/files.
        content = body.encode("utf-8")
        digest = hashlib.sha256(content).hexdigest()
        key, version = self.prepare(run_id, slot)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT owner,version,sha256 FROM objects WHERE key=?", (key,)
            ).fetchone()
            if existing and existing != (run_id, version, digest):
                raise ValueError(
                    "Object already exists with another owner, version or payload"
                )
            target = self.path(key, version)
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=target.parent, delete=False
                ) as output:
                    temporary = Path(output.name)
                    output.write(content)
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(temporary, 0o400)
                os.replace(temporary, target)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            if not existing:
                db.execute(
                    "INSERT INTO objects VALUES (?,?,?,?)",
                    (key, run_id, version, digest),
                )
            db.execute(
                "UPDATE intents SET state=? WHERE run_id=? AND slot=?",
                ("stored", run_id, slot),
            )
        return key

    def delete(self, run_id, slot):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT key,version FROM intents WHERE run_id=? AND slot=?",
                (run_id, slot),
            ).fetchone()
            if row is None:
                return
            key, version = row
            existing = db.execute(
                "SELECT owner,version FROM objects WHERE key=?", (key,)
            ).fetchone()
            if existing is not None and existing != (run_id, version):
                raise ValueError(
                    "Refusing to delete object belonging to another execution/version"
                )
            # Remove only the file identified by this durable intent, even after a lost response.
            self.path(key, version).unlink(missing_ok=True)
            db.execute(
                "DELETE FROM objects WHERE key=? AND owner=? AND version=?",
                (key, run_id, version),
            )
            db.execute(
                "DELETE FROM attachments WHERE run_id=? AND slot=?", (run_id, slot)
            )
            db.execute(
                "UPDATE intents SET state=? WHERE run_id=? AND slot=?",
                ("compensated", run_id, slot),
            )
