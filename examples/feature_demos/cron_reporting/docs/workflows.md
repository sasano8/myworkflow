# ワークフロー一覧

要求カタログ：cronによる日次レポート（example.daily_report）。固定IDはこの要求カタログ内で解決します。

[共有定義](shared-definitions.md)

| 固定ID | ワークフロー | 呼び出すロール | 配置数 |
| --- | --- | --- | --- |
| w.daily_report | [前日分の日次レポート作成](workflows/w.daily_report.md) | [システム](shared-definitions.md#role.report_system) | 1 |

## 未配置の共有定義

なし。

## ワークフローに未対応の受入条件

なし。
