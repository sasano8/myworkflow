# 窓口でのチケット発行

固定ID：ticket.workflow

[ワークフロー一覧](../workflows.md)

## 処理・配置

### ticket.binding

処理：[ticket.issue](../shared-definitions.md#ticket.issue)

ステップ：[ticket.lock](../shared-definitions.md#ticket.lock) → [ticket.save](../shared-definitions.md#ticket.save)

ロール割当：system → [role.system](../shared-definitions.md#role.system)

- ticket.trigger：担当者が発行を依頼／実行者：[ticket.operator](../shared-definitions.md#ticket.operator)
  入力元：[ticket.number](../shared-definitions.md#ticket.number) ← 受付番号


## ロール

- [role.system](../shared-definitions.md#role.system)：システム
- [ticket.operator](../shared-definitions.md#ticket.operator)：受付担当

## 状態・遷移

未定義。

## 接続・待機

未定義。

## データ

- [ticket.number](../shared-definitions.md#ticket.number)：受付番号
- [ticket.receipt](../shared-definitions.md#ticket.receipt)：発行結果

## 受入条件

- [受付担当がチケットを発行する](../acceptance.md#scenario.tickets.issue)：ticket.issue

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
