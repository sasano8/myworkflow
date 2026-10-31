"""SQLite object/intent model. This adapter does not implement the S3 API."""
from uuid import uuid4


class SQLiteObjectStore:
    def __init__(self, database):
        self.database = database

    def connect(self):
        return self.database.connect()

    def prepare(self, run_id, slot):
        key = f'purchase/{run_id}/{slot}'
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO intents VALUES (?,?,?,?,?)', (run_id, slot, key, str(uuid4()), 'pending'))
            intent = db.execute('SELECT key,version,state FROM intents WHERE run_id=? AND slot=?', (run_id, slot)).fetchone()
            if intent[2] == 'compensated':
                raise ValueError('Compensated run cannot be reused')
        return key, intent[1]

    def put(self, run_id, slot, body):
        key, version = self.prepare(run_id, slot)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT owner,version,body FROM objects WHERE key=?', (key,)).fetchone()
            if existing and existing != (run_id, version, body):
                raise ValueError('Object already exists with another owner, version or payload')
            if not existing:
                db.execute('INSERT INTO objects VALUES (?,?,?,?)', (key, run_id, version, body))
            db.execute('UPDATE intents SET state=? WHERE run_id=? AND slot=?', ('stored', run_id, slot))
        return key

    def delete(self, run_id, slot):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT key,version FROM intents WHERE run_id=? AND slot=?', (run_id, slot)).fetchone()
            if row is None:
                return
            key, version = row
            existing = db.execute('SELECT owner,version FROM objects WHERE key=?', (key,)).fetchone()
            if existing is not None and existing != (run_id, version):
                raise ValueError('Refusing to delete object belonging to another execution/version')
            db.execute('DELETE FROM objects WHERE key=? AND owner=? AND version=?', (key, run_id, version))
            db.execute('DELETE FROM attachments WHERE run_id=? AND slot=?', (run_id, slot))
            db.execute('UPDATE intents SET state=? WHERE run_id=? AND slot=?', ('compensated', run_id, slot))
