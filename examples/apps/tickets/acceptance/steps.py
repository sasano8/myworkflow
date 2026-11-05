from pytest_bdd import parsers
from myworkflow.acceptance import Definitions
from myworkflow.executable import Principal

steps = Definitions()


@steps.step(
    "Context",
    parsers.parse("受付担当が窓口を開いている"),
    actor="受付担当",
    refs=("ticket.binding",),
)
def open_counter(ctx):
    ctx.actor = Principal("operator", frozenset({"ticket.operator"}))


@steps.step(
    "Action",
    parsers.parse('受付番号 "{number}" を発行する'),
    actor="受付担当",
    refs=("ticket.issue",),
)
def issue(ctx, number):
    ctx.result = ctx.engine.invoke(
        "ticket.binding",
        "ticket.trigger",
        {"受付番号": number},
        ctx.actor,
        run_id="ticket-run",
    )


@steps.step(
    "Outcome",
    parsers.parse("チケットが1件保存され発行結果が返る"),
    actor="検証基盤",
    refs=("ticket.save",),
)
def check_ticket(ctx):
    with ctx.engine.services.database.connect() as db:
        numbers = [r[0] for r in db.execute("SELECT number FROM tickets").fetchall()]
    return numbers == ["T-001"] and ctx.result.code == 0
