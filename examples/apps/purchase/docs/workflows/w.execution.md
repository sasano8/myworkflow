# 承認済み購買申請の発注確定

固定ID：w.execution

[ワークフロー一覧](../workflows.md)

## 処理・配置

### b.confirm

処理：[p.confirm](../shared-definitions.md#p.confirm)

ステップ：[s.order-lock](../shared-definitions.md#s.order-lock) → [s.eligibility](../shared-definitions.md#s.eligibility) → [s.confirm](../shared-definitions.md#s.confirm) → [s.stop](../shared-definitions.md#s.stop)

ロール割当：system → [role.system](../shared-definitions.md#role.system)

- t.confirm：承認ワークフローから起動／実行者：[role.system](../shared-definitions.md#role.system)
  入力元：[a.id](../shared-definitions.md#a.id) ← id


## ロール

- [role.system](../shared-definitions.md#role.system)：システム

## 状態・遷移

未定義。

## 接続・待機

- [w.approval](w.approval.md)／b.dispatch → このワークフロー

## データ

- [a.id](../shared-definitions.md#a.id)：購買申請ID
- [a.status](../shared-definitions.md#a.status)：申請状態
- [a.eligible](../shared-definitions.md#a.eligible)：発注可能
- [a.order](../shared-definitions.md#a.order)：発注番号

## 受入条件

- [承認済みの購買申請を指定日時に一度だけ発注する](../acceptance.md#scenario.purchase.schedule)：p.confirm
- [却下した購買申請は予定日時を過ぎても発注しない](../acceptance.md#scenario.purchase.reject)：p.confirm
- [承認済みでも見積書がなければ発注できない](../acceptance.md#scenario.purchase.missing-quotes)：p.confirm
- [承認待ちを経て発注が一度だけ確定する](../acceptance.md#scenario.purchase.temporal-approve)：w.execution

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
