# サンプル銀行：業務要求の概要

> 自動生成：ルートカタログと要求カタログの定義から生成します。文書を直接編集せず、元の定義を変更してください。

ルートID：org.example

サンプル銀行を入口として、2件の要求カタログをまとめています。

## 対象業務

| 要求カタログID | 要求カタログ | ワークフロー | 処理 | 主なステップ |
| --- | --- | --- | --- | --- |
| product.insurance | [保険商品](catalogs/product.insurance/workflows.md) | [保険申込の業務](catalogs/product.insurance/workflows/w.main.md) | 保険申込の処理 | 申込内容の確認、保険料の算定、審査資料の作成 |
| product.loan | [融資商品](catalogs/product.loan/workflows.md) | [融資申込の業務](catalogs/product.loan/workflows/w.main.md) | 融資申込の処理 | 申込内容の確認、返済計画の計算 |

## ルートと要求カタログの関係

- ルートカタログ：サンプル銀行。要求カタログを一覧にまとめます。
- 要求カタログ：ワークフロー、処理、データ、担当ロールを管理する名前空間です。
- 詳細：要求カタログの一覧からワークフロー詳細と共有定義へ進みます。

定義の固定IDは要求カタログ内で解決します。外から参照するときは、要求カタログIDと定義IDを指定します。

## 複数カタログで共有するロール

| ロールID | 正式名 | 表示名 | 参照する要求カタログ |
| --- | --- | --- | --- |
| role.operator | 商品運用部の業務担当者 | 業務担当者 | [保険商品](catalogs/product.insurance/shared-definitions.md#role.operator)、[融資商品](catalogs/product.loan/shared-definitions.md#role.operator) |
| role.system | 商品業務システム | システム | [保険商品](catalogs/product.insurance/shared-definitions.md#role.system)、[融資商品](catalogs/product.loan/shared-definitions.md#role.system) |

## 定義の範囲

この概要にはルートに含まれる要求カタログの宣言内容を表示します。一覧のステップは宣言順の集約であり、商品間の実行順序や接続を表すものではありません。

受入条件・実装状況・実行履歴はこのルート定義には含まれていません。実行負荷・データ・権限の分離は別途設計します。

## 詳細

[要求カタログ一覧](catalogs.md)
