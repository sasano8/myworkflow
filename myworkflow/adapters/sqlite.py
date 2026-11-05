"""SQLite connection and execution journal; no advisory-lock claim."""

from contextlib import contextmanager
import json
import sqlite3


class SQLiteDatabase:
    def __init__(self, path):
        self.path = str(path)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=2)
        try:
            with db:
                yield db
        finally:
            db.close()


class SQLiteExecutionStore:
    def __init__(self, database):
        self.database = database
        with self.database.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, status TEXT, events TEXT)"
            )

    def begin(self, run_id):
        if not run_id or "/" in run_id:
            raise ValueError("Use a nonempty execution ID without slashes")
        with self.database.connect() as db:
            db.execute("INSERT INTO runs VALUES (?,?,?)", (run_id, "running", "[]"))

    def record(self, run_id, events, status):
        with self.database.connect() as db:
            db.execute(
                "UPDATE runs SET status=?,events=? WHERE id=?",
                (str(status), json.dumps(events), run_id),
            )
            if not db.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone():
                raise ValueError(f"{run_id}: journal entry does not exist")

    def get(self, run_id):
        with self.database.connect() as db:
            row = db.execute(
                "SELECT status,events FROM runs WHERE id=?", (run_id,)
            ).fetchone()
        if row is None:
            raise ValueError(f"{run_id}: unknown execution")
        return row[0], json.loads(row[1])
