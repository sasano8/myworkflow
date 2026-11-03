# 融資申込の業務

固定ID：w.main

[ワークフロー一覧](../workflows.md)

ルート：サンプル銀行（org.example）／要求カタログ：融資商品（product.loan）。固定IDはこの要求カタログ内で解決します。

## 処理・配置

### b.process

処理：[p.process](../shared-definitions.md#p.process)

ステップ：[s.check](../shared-definitions.md#s.check) → [s.calculate](../shared-definitions.md#s.calculate)

ロール割当：system → [role.system](../shared-definitions.md#role.system)

- t.request：融資申込の処理依頼／実行者：[role.operator](../shared-definitions.md#role.operator)
  入力元：[a.request](../shared-definitions.md#a.request) ← request


## ロール

- [role.operator](../shared-definitions.md#role.operator)：業務担当者
- [role.system](../shared-definitions.md#role.system)：システム

## 状態・遷移

未定義。

## 接続・待機

未定義。

## データ

- [a.request](../shared-definitions.md#a.request)：融資申込

## 受入条件

未定義。

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。

[要求カタログ一覧](../../../catalogs.md)
