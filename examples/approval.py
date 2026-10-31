"""Approval, durable wait declarations, reuse, and workflow handoff."""
from myworkflow import Artifact, Binding, Catalog, Lock, Pipeline, Step, Trigger, Use, Workflow, render

catalog = Catalog(
    artifacts=(
        Artifact("a.application", "購買申請"), Artifact("a.id", "申請ID"),
        Artifact("a.result", "受付結果"), Artifact("a.wait", "待機状態"),
        Artifact("a.quote", "見積書ファイル"), Artifact("a.attachment", "見積書登録情報"),
        Artifact("a.order", "発注情報"),
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
        Pipeline("p.dispatch", "発注確定開始", ("a.id",), (), (
            Step("s.dispatch", "発注確定への引継ぎ", "承認済みの購買申請IDを発注確定ワークフローに引き継ぐ。", (Use("a.id", "参照"),)),
        ), reply=False),
        Pipeline("p.upload", "見積書登録", ("a.id", "a.quote"), ("a.attachment",), (
            Lock("s.upload-lock", "添付更新の排他制御", ("a.id",)),
            Step("s.check-attachment", "添付可否確認", "購買申請の存在と申請者の更新権限を確認する。", (Use("a.application", "DB読取"),)),
            Step("s.store-attachment", "見積書保存", "見積書ファイルを保存し、購買申請に紐づく登録情報を記録する。", (Use("a.quote", "参照"), Use("a.attachment", "DB作成"), Use("a.attachment", "保持"))),
        )),
        Pipeline("p.confirm", "発注確定", ("a.id",), (), (
            Lock("s.order-lock", "発注の排他制御", ("a.id",)),
            Step("s.check-order", "発注条件確認", "購買申請が承認済みで、見積書が登録され、まだ発注されていないことを確認する。条件を満たさなければ確定しない。", (Use("a.application", "DB読取"), Use("a.attachment", "DB読取"), Use("a.order", "DB読取"))),
            Step("s.confirm-order", "発注確定", "購買申請の明細・取引先・金額から発注情報を作成し、購買申請を発注確定済みに更新する。両更新は同一トランザクションで行う。", (Use("a.application", "参照"), Use("a.order", "DB作成"), Use("a.application", "DB更新"))),
        ), reply=False),
    ),
    workflows=(
        Workflow("w.approval", "購買申請の受付・承認", (
            Binding("b.submit", "p.submit", "ユーザーがFEから申請", (("a.application", "HTTPリクエスト本文"),)),
            Binding("b.approve", "p.approve", "承認者がFEで承認", (("a.id", "承認イベントの申請ID"),), after="b.submit", wait="申請IDが一致する承認イベントを受信"),
            Binding("b.timer", "p.dispatch", "指定日時に到達", (("a.id", "永続化した待機状態"),), after="b.approve", wait="承認済みかつ実行希望日時に到達", next_workflow_id="w.execution", additional_triggers=(
                Trigger("t.approved-manual", "承認済み申請をユーザーがFEで実行", (("a.id", "HTTPリクエスト本文"),), after="b.approve", wait="承認済みであること"),
            )),
        )),
        Workflow("w.manual", "購買申請への見積書添付", (
            Binding("b.manual", "p.upload", "申請者がFEで見積書をアップロード", (("a.id", "HTTPリクエストの申請ID"), ("a.quote", "アップロードしたファイル"))),
        )),
        Workflow("w.execution", "承認済み購買申請の発注確定", (
            Binding("b.confirm", "p.confirm", "購買申請の承認ワークフローから起動", (("a.id", "起動元から引き継いだ購買申請ID"),)),
        )),
    ),
)

if __name__ == "__main__":
    print(render(catalog), end="")
