# language: ja
@temporal
機能: Temporalによる購買フローの受入条件

  @scenario.purchase.temporal-approve @req.w.approval @req.w.execution
  シナリオ: 承認待ちを経て発注が一度だけ確定する
    前提 Temporalで購買申請が承認待ちになっている
    ならば 発注は0件である
    もし 承認者が承認する
    かつ 同じ承認イベントを再送する
    かつ ワークフローの完了を待つ
    ならば 発注は1件である
    かつ 申請状態は "発注確定済み" である

  @scenario.purchase.temporal-reject @req.w.approval @req.p.approve
  シナリオ: Temporalでも却下した申請を発注しない
    前提 Temporalで購買申請が承認待ちになっている
    もし 承認者が却下する
    かつ ワークフローの完了を待つ
    ならば 発注は0件である
    かつ 申請状態は "却下済み" である
