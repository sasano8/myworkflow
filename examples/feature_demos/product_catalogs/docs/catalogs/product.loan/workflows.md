# ワークフロー一覧

ルート：サンプル銀行（org.example）／要求カタログ：融資商品（product.loan）。固定IDはこの要求カタログ内で解決します。

[共有定義](shared-definitions.md)

| 固定ID | ワークフロー | 呼び出すロール | 配置数 |
| --- | --- | --- | --- |
| w.main | [融資申込の業務](workflows/w.main.md) | [業務担当者](shared-definitions.md#role.operator) | 1 |

## 未配置の共有定義

なし。

## ワークフローに未対応の受入条件

なし。

[要求カタログ一覧](../../catalogs.md)
