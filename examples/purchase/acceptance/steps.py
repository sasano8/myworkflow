"""Gherkin step implementations for the sample's business acceptance tests."""
from pytest_bdd import parsers

from examples.purchase.scheduling import ScheduledPurchase, aware_time
from myworkflow.acceptance import Definitions

steps = Definitions()


def given(pattern, actor, refs):
    return steps.step('Context', parsers.parse(pattern), actor=actor, refs=refs)


def when(pattern, actor, refs):
    return steps.step('Action', parsers.parse(pattern), actor=actor, refs=refs)


def then(pattern, actor, refs):
    return steps.step('Outcome', parsers.parse(pattern), actor=actor, refs=refs)


@given('テスト時計は "{instant}" である', 'テスト時計', ('w.approval',))
def clock(ctx, instant):
    ctx.clock.instant = aware_time(instant)


@given('発注予定日時は "{instant}" である', 'テスト基盤', ('w.approval',))
def schedule(ctx, instant):
    ctx.flow = ScheduledPurchase(ctx.engine, ctx.clock, instant)


@given('見積書2件を添付した承認待ちの購買申請がある', '申請者', ('p.submit', 'p.upload'))
def with_quotes(ctx):
    ctx.prepare(quotes=True)


@given('見積書のない承認待ちの購買申請がある', '申請者', ('p.submit',))
def without_quotes(ctx):
    ctx.prepare(quotes=False)


@given('保存障害は "{fault}" である', '障害注入基盤', ('p.upload',))
def failures(ctx, fault):
    rules = {
        '障害なし': {}, '見積書Aが2回とも保存前に失敗': {'put-A': ['before', 'before']},
        '見積書Bが1回だけ保存前に失敗': {'put-B': ['before']}, '見積書Bが1回だけ保存後に応答消失': {'put-B': ['after']},
        '見積書Bが2回とも保存前に失敗': {'put-B': ['before', 'before']}, '見積書Bが2回とも保存後に応答消失': {'put-B': ['after', 'after']},
        '見積書Bが最終失敗し見積書Aの削除も失敗': {'put-B': ['before', 'before'], 'delete-A': ['before']},
    }
    ctx.services.failures = rules[fault]


@given('Temporalで購買申請が承認待ちになっている', '申請者・Temporal', ('w.approval',))
def temporal_wait(ctx):
    ctx.start_temporal()


@when('承認者が承認する', '承認者', ('b.approve',))
def approve(ctx):
    ctx.decide(True)


@when('承認者が却下する', '承認者', ('b.approve',))
def reject(ctx):
    ctx.decide(False)


@when('同じ承認イベントを再送する', '承認者', ('w.approval',))
def duplicate(ctx):
    ctx.decide(True)


@when('時計を "{instant}" に進める', 'テスト時計', ('w.approval',))
def advance(ctx, instant):
    ctx.advance(instant)


@when('申請者が承認を試みる', '申請者', ('b.approve',))
def unauthorized(ctx):
    ctx.attempt(lambda: ctx.decide(True, ctx.applicant))


@when('発注確定を試みる', 'システム', ('p.confirm',))
def confirm(ctx):
    ctx.attempt(lambda: ctx.invoke('b.confirm', 't.confirm', {'id': 'purchase-001'}, ctx.system))


@when('申請者が見積書2件を登録する', '申請者', ('p.upload',))
def upload(ctx):
    ctx.attempt(ctx.upload)


@when('保存基盤を開き直して手動復旧する', '復旧担当者', ('c.delete-a', 'c.delete-b'))
def recover(ctx):
    ctx.attempt(ctx.recover)


@when('残存ファイルが別の実行のバージョンに置き換わる', '障害注入基盤', ('c.delete-a',))
def replace_owner(ctx):
    with ctx.services.connect() as db:
        db.execute("UPDATE objects SET owner='other-execution', version='other-version'")


@when('ワークフローの完了を待つ', 'テスト基盤', ('w.approval',))
def wait_completed(ctx):
    ctx.driver.finish()


@then('発注は{count:d}件である', '検証基盤', ('p.confirm',))
def order_count(ctx, count):
    return ctx.count('orders') == count


@then('申請状態は "{status}" である', '検証基盤', ('p.submit', 'p.approve', 'p.confirm'))
def application_status(ctx, status):
    expected = {'承認待ち': 'waiting-approval', '承認済み': 'approved', '却下済み': 'rejected', '発注確定済み': 'confirmed'}[status]
    return ctx.status() == expected


@then('最後の操作は権限不足である', '検証基盤', ('b.approve',))
def permission_denied(ctx):
    return isinstance(ctx.error, PermissionError)


@then('最後の操作は失敗である', '検証基盤', ('p.confirm',))
def failed(ctx):
    from myworkflow.executable import ExecutionFailed
    return isinstance(ctx.error, ExecutionFailed)


@then('最後の操作の結果は "{result}" である', '検証基盤', ('p.upload',))
def result(ctx, result):
    if result not in ('成功', '失敗'):
        raise ValueError('Unknown expected result')
    return (ctx.error is None) == (result == '成功')


@then('今回の保存物は{count:d}件である', '検証基盤', ('p.upload',))
def objects(ctx, count):
    return ctx.count('objects') == count


@then('添付登録は{count:d}件である', '検証基盤', ('p.upload',))
def attachments(ctx, count):
    return ctx.count('attachments') == count


@then('補償呼出しは{count:d}件である', '検証基盤', ('c.delete-a', 'c.delete-b'))
def compensations(ctx, count):
    return sum(call.startswith('delete-') for call in ctx.services.calls) == count


@then('復旧状態は "{status}" である', '検証基盤', ('c.delete-a',))
def recovery_state(ctx, status):
    expected = {'手動復旧待ち': 'manual-recovery', '補償完了': 'compensated'}[status]
    return ctx.run_status() == expected


@then('別の実行のファイルは{count:d}件である', '検証基盤', ('c.delete-a',))
def other_objects(ctx, count):
    with ctx.services.connect() as db:
        actual = db.execute('SELECT count(*) FROM objects WHERE owner=? AND version=?', ('other-execution', 'other-version')).fetchone()[0]
    return actual == count
