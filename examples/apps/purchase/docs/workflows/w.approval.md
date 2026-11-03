# 購買申請の受付・承認

固定ID：w.approval

[ワークフロー一覧](../workflows.md)

## 処理・配置

### b.submit

処理：[p.submit](../shared-definitions.md#p.submit)

ステップ：[s.submit-lock](../shared-definitions.md#s.submit-lock) → [s.submit](../shared-definitions.md#s.submit)

ロール割当：system → [role.system](../shared-definitions.md#role.system)

- t.submit：申請者がFEで申請／実行者：[role.requester](../shared-definitions.md#role.requester)
  入力元：[a.id](../shared-definitions.md#a.id) ← id、[a.vendor](../shared-definitions.md#a.vendor) ← vendor、[a.amount](../shared-definitions.md#a.amount) ← amount

### b.approve

処理：[p.approve](../shared-definitions.md#p.approve)

ステップ：[s.approve-lock](../shared-definitions.md#s.approve-lock) → [s.check-approval](../shared-definitions.md#s.check-approval) → [s.approve](../shared-definitions.md#s.approve) → [s.reject](../shared-definitions.md#s.reject)

ロール割当：system → [role.system](../shared-definitions.md#role.system)

- t.approve：承認者がFEで承認または却下／実行者：[role.approver](../shared-definitions.md#role.approver)
  入力元：[a.id](../shared-definitions.md#a.id) ← id、[a.decision](../shared-definitions.md#a.decision) ← decision

### b.dispatch

処理：[p.dispatch](../shared-definitions.md#p.dispatch)

ステップ：[s.dispatch](../shared-definitions.md#s.dispatch)

ロール割当：system → [role.system](../shared-definitions.md#role.system)

- t.timer：指定日時に到達／実行者：[role.system](../shared-definitions.md#role.system)
  入力元：[a.id](../shared-definitions.md#a.id) ← id

- t.manual：発注担当者がFEで開始／実行者：[role.buyer](../shared-definitions.md#role.buyer)
  入力元：[a.id](../shared-definitions.md#a.id) ← application


## ロール

- [role.requester](../shared-definitions.md#role.requester)：申請者
- [role.approver](../shared-definitions.md#role.approver)：承認者
- [role.buyer](../shared-definitions.md#role.buyer)：発注担当者
- [role.system](../shared-definitions.md#role.system)：システム

## 状態・遷移

未定義。

## 接続・待機

- t.approve：先行配置 未定義／待機条件 承認イベントを受信
- t.timer：先行配置 未定義／待機条件 承認済みかつ指定日時に到達
- b.dispatch → [w.execution](w.execution.md)

## データ

- [a.id](../shared-definitions.md#a.id)：購買申請ID
- [a.vendor](../shared-definitions.md#a.vendor)：取引先
- [a.amount](../shared-definitions.md#a.amount)：申請金額
- [a.status](../shared-definitions.md#a.status)：申請状態
- [a.decision](../shared-definitions.md#a.decision)：承認判断

## 受入条件

- [承認済みの購買申請を指定日時に一度だけ発注する](../acceptance.md#scenario.purchase.schedule)：w.approval
- [却下した購買申請は予定日時を過ぎても発注しない](../acceptance.md#scenario.purchase.reject)：p.approve
- [申請者のロールでは承認できない](../acceptance.md#scenario.purchase.authorization)：b.approve
- [承認待ちを経て発注が一度だけ確定する](../acceptance.md#scenario.purchase.temporal-approve)：w.approval
- [Temporalでも却下した申請を発注しない](../acceptance.md#scenario.purchase.temporal-reject)：w.approval、p.approve

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
