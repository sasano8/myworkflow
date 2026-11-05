from myworkflow.adapters.sqlite import SQLiteDatabase, SQLiteExecutionStore
from myworkflow.executable import Engine, Principal, Registry
from myworkflow.adapters.inprocess import InProcessLockProvider
from .contract import program
from .steps import save_ticket


registry = Registry()
registry.register(save_ticket)


class TicketRepository:
    def __init__(self, database):
        self.database = database
        with database.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS tickets(number TEXT PRIMARY KEY)")

    def create_ticket(self, number):
        with self.database.connect() as db:
            db.execute("INSERT INTO tickets VALUES (?)", (number,))


def engine(database, *, locks=None):
    db = SQLiteDatabase(database)
    return Engine(
        program,
        registry,
        TicketRepository(db),
        locks=locks or InProcessLockProvider(),
        store=SQLiteExecutionStore(db),
    )
