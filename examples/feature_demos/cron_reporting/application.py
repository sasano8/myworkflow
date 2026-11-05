"""One-shot runner; report uniqueness is enforced by SQLite, not cron timing."""

from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from myworkflow import annotate
from myworkflow.adapters.sqlite import SQLiteDatabase, SQLiteExecutionStore
from myworkflow.executable import Context, Engine, Principal, Program, Registry
from . import contract as c

program = Program.from_catalog(c.CATALOG)
registry = Registry()


@annotate(c.create_report)
def create_report(ctx: Context) -> None:
    day = date.fromisoformat(ctx.values["business_date"]).isoformat()
    # A fixed sample body demonstrates idempotent persistence, not a real aggregation.
    body = f"{day}の日次レポート（サンプル）"
    with ctx.services.connect() as db:
        db.execute(
            "INSERT INTO reports VALUES (?, ?) ON CONFLICT(business_date) DO NOTHING",
            (day, body),
        )
        ctx.values["report"] = db.execute(
            "SELECT body FROM reports WHERE business_date=?", (day,)
        ).fetchone()[0]
    ctx.add_message(ctx.values["report"])


registry.register(create_report)


def target_date(now=None):
    zone = ZoneInfo(c.SCHEDULE.timezone)
    if now is not None and (now.tzinfo is None or now.utcoffset() is None):
        raise ValueError("now must include a timezone")
    instant = datetime.now(zone) if now is None else now.astimezone(zone)
    return (instant.date() - timedelta(days=1)).isoformat()


def run(database, day):
    day = date.fromisoformat(day).isoformat()
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = SQLiteDatabase(path)
    with db.connect() as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS reports(business_date TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
    engine = Engine(program, registry, db, store=SQLiteExecutionStore(db))
    principal = Principal("cron.daily_report", frozenset({c.system.id}))
    return engine.invoke_or_raise(
        c.placement.id,
        c.requested.id,
        {"business_date": day},
        principal,
        run_id="report-" + uuid4().hex,
    )
