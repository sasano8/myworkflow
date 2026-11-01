"""Compatibility facade composing the purchase sample's independent adapters."""
from myworkflow.adapters.sqlite import SQLiteDatabase, SQLiteExecutionStore
from myworkflow.locking import InProcessLockProvider
from examples.apps.purchase.object_store import FileObjectStore
from examples.apps.purchase.recovery import Recovery
from examples.apps.purchase.testing import Faults, ObservedObjectStore, ObservedRepository


class Services:
    def __init__(self, database, *, locks=None):
        self.database = str(database)
        self.db = SQLiteDatabase(database)
        self.lock_provider = locks if locks is not None else InProcessLockProvider()
        self.execution_store = SQLiteExecutionStore(self.db)
        self.faults = Faults()
        self.repository = ObservedRepository(self.db, self.faults)
        self.objects = ObservedObjectStore(FileObjectStore(self.db), self.faults)
        self.recovery = Recovery(self.execution_store, self.objects)
        with self.connect() as db:
            columns = {r[1] for r in db.execute('PRAGMA table_info(objects)')}
            if 'body' in columns:
                if db.execute('SELECT 1 FROM objects LIMIT 1').fetchone():
                    raise ValueError('Legacy blob bodies need explicit export before using the file-backed store')
                db.execute('ALTER TABLE objects RENAME COLUMN body TO sha256')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS applications(id TEXT PRIMARY KEY, owner TEXT, vendor TEXT, amount INTEGER, status TEXT);
                CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY, application_id TEXT UNIQUE);
                CREATE TABLE IF NOT EXISTS objects(key TEXT PRIMARY KEY, owner TEXT, version TEXT, sha256 TEXT);
                CREATE TABLE IF NOT EXISTS intents(run_id TEXT, slot TEXT, key TEXT, version TEXT, state TEXT, PRIMARY KEY(run_id, slot));
                CREATE TABLE IF NOT EXISTS attachments(application_id TEXT, run_id TEXT, slot TEXT, key TEXT, PRIMARY KEY(application_id, slot));
            ''')

    def connect(self): return self.db.connect()
    def lock(self, key): return self.lock_provider.acquire(key)
    def begin(self, run_id): return self.execution_store.begin(run_id)
    def record(self, run_id, events, status): return self.execution_store.record(run_id, events, status)
    def put(self, run_id, slot, body): return self.objects.put(run_id, slot, body)
    def delete(self, run_id, slot): return self.objects.delete(run_id, slot)
    def recover(self, run_id, *, interrupted=False):
        return self.recovery.recover(run_id, confirmed_stopped=interrupted)

    @property
    def failures(self): return self.faults.rules
    @failures.setter
    def failures(self, value): self.faults.rules = value
    @property
    def calls(self): return self.faults.calls

    def __getattr__(self, name):
        if name in ('application', 'submit', 'check_upload', 'decide', 'eligible', 'confirm', 'register_attachments'):
            return getattr(self.repository, name)
        raise AttributeError(name)
