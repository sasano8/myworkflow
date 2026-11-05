from myworkflow import annotate, declaration
from myworkflow.adapters.sqlite import SQLiteDatabase, SQLiteExecutionStore
from myworkflow.executable import Context, Engine, Principal, Registry
from myworkflow.adapters.inprocess import InProcessLockProvider
from examples.apps.tickets.contract import (
    TicketNumber,
    TicketReceipt,
    program,
    save_ticket,
)


@annotate(save_ticket)
def issue(ctx: Context) -> None:
    ctx.services.issue(ctx.values[declaration(TicketNumber).key])
    ctx.values[declaration(TicketReceipt).key] = (
        "発行済み:" + ctx.values[declaration(TicketNumber).key]
    )


registry = Registry()
registry.register(issue)


class TicketRepository:
    def __init__(self, database):
        self.database = database
        with database.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS tickets(number TEXT PRIMARY KEY)")

    def issue(self, number):
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
