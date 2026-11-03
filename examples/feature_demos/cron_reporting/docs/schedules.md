# 定期実行一覧

起動時刻は外部のcronが管理します。この文書の生成ではスケジュールを登録しません。

[ワークフロー一覧](workflows.md)

| スケジュールID | 名前 | cron式 | タイムゾーン | ワークフロー | 配置ID | トリガーID | 実行ロール |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cron.daily_report | 毎日6時に前日分を作成 | 0 6 * * * | Asia/Tokyo | [前日分の日次レポート作成](workflows/w.daily_report.md) | b.daily_report | t.daily_cron | [システム](shared-definitions.md#role.report_system) |

cron式は数値によるUNIXの5項目（分・時・日・月・曜日）です。`*`・列挙・範囲・間隔を使用でき、秒・年・名前付き曜日・マクロは対象外です。
