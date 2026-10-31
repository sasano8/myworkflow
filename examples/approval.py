"""Approval, durable wait declarations, reuse, and workflow handoff."""
from myworkflow import Artifact, Binding, Catalog, Lock, Pipeline, Step, Trigger, Use, Workflow, render

catalog = Catalog(
    artifacts=(
        Artifact("a.application", "申請"), Artifact("a.id", "申請ID"),
        Artifact("a.result", "受付結果"), Artifact("a.wait", "待機状態"),
    ),
    pipelines=(
        Pipeline("p.submit", "申請受付", ("a.application",), ("a.result",), (
            Step("s.save", "申請保存", "申請を承認待ちとして保存する。", (Use("a.application", "DB作成"), Use("a.id", "保持"))),
            Step("s.wait", "承認待ち登録", "申請IDに対応する承認イベントを待つ状態を永続化する。", (Use("a.id", "参照"), Use("a.wait", "DB作成"))),
        )),
        Pipeline("p.approve", "承認反映", ("a.id",), (), (
            Lock("s.lock", "申請の排他制御", ("a.id",)),
            Step("s.approve", "承認反映", "承認権限と現在の状態を確認して承認済みに更新する。", (Use("a.application", "DB読取"), Use("a.application", "DB更新"))),
            Step("s.schedule", "実行待ち登録", "指定日時までの待機状態を永続化する。", (Use("a.wait", "DB更新"),)),
        )),
        Pipeline("p.dispatch", "実行開始", ("a.id",), (), (
            Step("s.dispatch", "実行引継ぎ", "申請IDを次ワークフローに引き継ぐ。", (Use("a.id", "参照"),)),
        ), reply=False),
    ),
    workflows=(
        Workflow("w.approval", "申請・承認", (
            Binding("b.submit", "p.submit", "ユーザーがFEから申請", (("a.application", "HTTPリクエスト本文"),)),
            Binding("b.approve", "p.approve", "承認者がFEで承認", (("a.id", "承認イベントの申請ID"),), after="b.submit", wait="申請IDが一致する承認イベントを受信"),
            Binding("b.timer", "p.dispatch", "指定日時に到達", (("a.id", "永続化した待機状態"),), after="b.approve", wait="承認済みかつ実行希望日時に到達", next_workflow_id="w.execution", additional_triggers=(
                Trigger("t.approved-manual", "承認済み申請をユーザーがFEで実行", (("a.id", "HTTPリクエスト本文"),), after="b.approve", wait="承認済みであること"),
            )),
        )),
        Workflow("w.manual", "手動実行", (
            Binding("b.manual", "p.dispatch", "ユーザーがFEで実行", (("a.id", "HTTPリクエスト本文"),), next_workflow_id="w.execution"),
        )),
        Workflow("w.execution", "申請実行", ()),
    ),
)

if __name__ == "__main__":
    print(render(catalog), end="")
