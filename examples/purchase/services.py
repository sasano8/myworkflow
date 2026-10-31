"""SQLite demo adapters; object storage models S3 ownership, not the S3 API."""
from contextlib import contextmanager
import json
import sqlite3
import threading
from uuid import uuid4

from myworkflow.executable import RetryableError


class Services:
    def __init__(self, database):
        self.database = str(database)
        self.failures = {}
        self.calls = []
        self.locks = {}
        self.guard = threading.Lock()
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS applications(id TEXT PRIMARY KEY, owner TEXT, vendor TEXT, amount INTEGER, status TEXT);
                CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY, application_id TEXT UNIQUE);
                CREATE TABLE IF NOT EXISTS objects(key TEXT PRIMARY KEY, owner TEXT, version TEXT, body TEXT);
                CREATE TABLE IF NOT EXISTS intents(run_id TEXT, slot TEXT, key TEXT, version TEXT, state TEXT, PRIMARY KEY(run_id, slot));
                CREATE TABLE IF NOT EXISTS attachments(application_id TEXT, run_id TEXT, slot TEXT, key TEXT, PRIMARY KEY(application_id, slot));
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, status TEXT, events TEXT);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=2)
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def lock(self, key):
        with self.guard:
            lock = self.locks.setdefault(key, threading.Lock())
        if not lock.acquire(blocking=False):
            raise RuntimeError(f"Lock conflict: {key}")
        try:
            yield
        finally:
            lock.release()

    def begin(self, run_id):
        if not run_id or '/' in run_id:
            raise ValueError('Use a nonempty execution ID without slashes')
        with self.connect() as db:
            db.execute('INSERT INTO runs VALUES (?,?,?)', (run_id, 'running', '[]'))

    def record(self, run_id, events, status):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO runs VALUES (?, ?, ?)', (run_id, status, json.dumps(events)))

    def application(self, identity):
        with self.connect() as db:
            row = db.execute('SELECT owner,vendor,amount,status FROM applications WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise ValueError('Unknown application')
        return dict(zip(('owner', 'vendor', 'amount', 'status'), row))

    def submit(self, identity, actor, vendor, amount):
        if amount <= 0 or not vendor.strip():
            raise ValueError('Positive amount and vendor are required')
        with self.connect() as db:
            db.execute('INSERT INTO applications VALUES (?,?,?,?,?)', (identity, actor, vendor, amount, 'waiting-approval'))

    def check_upload(self, identity, actor):
        a = self.application(identity)
        if a['owner'] != actor:
            raise PermissionError('Only the applicant can attach quotations')
        if a['status'] != 'waiting-approval':
            raise ValueError('Attachments require waiting-approval state')

    def decide(self, identity, actor, approved):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT owner,status FROM applications WHERE id=?', (identity,)).fetchone()
            if row is None or row[1] != 'waiting-approval':
                raise ValueError('Application is not awaiting approval')
            if row[0] == actor:
                raise PermissionError('Applicant cannot approve their own application')
            status = 'approved' if approved else 'rejected'
            db.execute('UPDATE applications SET status=? WHERE id=?', (status, identity))
            return status

    def eligible(self, identity):
        a = self.application(identity)
        with self.connect() as db:
            count = db.execute('SELECT count(*) FROM attachments WHERE application_id=?', (identity,)).fetchone()[0]
            existing = db.execute('SELECT count(*) FROM orders WHERE application_id=?', (identity,)).fetchone()[0]
        return a['status'] == 'approved' and count == 2 and existing == 0

    def confirm(self, identity):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            a = db.execute('SELECT status FROM applications WHERE id=?', (identity,)).fetchone()
            count = db.execute('SELECT count(*) FROM attachments WHERE application_id=?', (identity,)).fetchone()[0]
            if a is None or a[0] != 'approved' or count != 2:
                raise ValueError('Order conditions are not satisfied')
            order_id = f'order-{identity}'
            db.execute('INSERT INTO orders VALUES (?,?)', (order_id, identity))
            self.inject('confirm', 'after-insert')
            db.execute('UPDATE applications SET status=? WHERE id=?', ('confirmed', identity))
            return order_id

    def inject(self, operation, point):
        queue = self.failures.get(operation, [])
        if queue and queue[0] == point:
            queue.pop(0)
            raise RetryableError(f'Injected {operation}:{point}')

    def put(self, run_id, slot, body):
        self.calls.append(f'put-{slot}')
        key = f'purchase/{run_id}/{slot}'
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO intents VALUES (?,?,?,?,?)', (run_id, slot, key, str(uuid4()), 'pending'))
            intent = db.execute('SELECT key,version,state FROM intents WHERE run_id=? AND slot=?', (run_id, slot)).fetchone()
            if intent[2] == 'compensated':
                raise ValueError('Compensated run cannot be reused')
        self.inject(f'put-{slot}', 'before')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT owner,version,body FROM objects WHERE key=?', (key,)).fetchone()
            if existing and existing != (run_id, intent[1], body):
                raise ValueError('Object already exists with another owner, version or payload')
            if not existing:
                db.execute('INSERT INTO objects VALUES (?,?,?,?)', (key, run_id, intent[1], body))
            db.execute('UPDATE intents SET state=? WHERE run_id=? AND slot=?', ('stored', run_id, slot))
        self.inject(f'put-{slot}', 'after')
        return key

    def register_attachments(self, identity, run_id):
        with self.connect() as db:
            for slot in ('A', 'B'):
                row = db.execute('SELECT key FROM intents WHERE run_id=? AND slot=? AND state=?', (run_id, slot, 'stored')).fetchone()
                if row is None:
                    raise ValueError('Missing object intent')
                db.execute('INSERT INTO attachments VALUES (?,?,?,?)', (identity, run_id, slot, row[0]))

    def delete(self, run_id, slot):
        self.calls.append(f'delete-{slot}')
        self.inject(f'delete-{slot}', 'before')
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

    def recover(self, run_id, *, interrupted=False):
        with self.connect() as db:
            row = db.execute('SELECT status,events FROM runs WHERE id=?', (run_id,)).fetchone()
        if row is None or (row[0] not in ('manual-recovery', 'failed', 'compensated') and not (interrupted and row[0] == 'running')):
            raise ValueError('Only failed or compensation-pending runs can be recovered')
        events = json.loads(row[1])
        for slot in ('B', 'A'):
            self.delete(run_id, slot)
        self.record(run_id, events + [('recovery', 'compensated')], 'compensated')
