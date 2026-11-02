from myworkflow import annotate
from myworkflow.adapters.sqlite import SQLiteDatabase, SQLiteExecutionStore
from myworkflow.executable import Context, Engine, Principal, Program, Registry
from myworkflow.adapters.inprocess import InProcessLockProvider
from examples.apps.tickets.contract import SPEC

program = Program(SPEC)


@annotate(program.steps['ticket.save'])
def issue(ctx: Context) -> None:
    ctx.services.issue(ctx.values['number'])
    ctx.values['receipt'] = '発行済み:' + ctx.values['number']


registry = Registry()
registry.register(issue)

class TicketRepository:
    def __init__(self, database):
        self.database = database
        with database.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS tickets(number TEXT PRIMARY KEY)')

    def issue(self, number):
        with self.database.connect() as db:
            db.execute('INSERT INTO tickets VALUES (?)', (number,))


def engine(database, *, locks=None):
    db = SQLiteDatabase(database)
    return Engine(program, registry, TicketRepository(db),
                  locks=locks or InProcessLockProvider(), store=SQLiteExecutionStore(db))
