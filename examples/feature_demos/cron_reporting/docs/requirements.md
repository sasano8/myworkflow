# 業務要件

要求カタログ：cronによる日次レポート（example.daily_report）

## ロール一覧

| ロールID | 業務上の正式名 | 表示名 |
| --- | --- | --- |
| role.report_system | 日次レポート実行システム | システム |

## 001 前日分の日次レポート作成

### 001-00001 日次レポート作成

| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001-00001-00000 | トリガー1：cronの定期起動 | システム | 受付 | 入力元：集計対象日 ← business_date | 入力：集計対象日 | — | w.daily_report/b.daily_report/p.daily_report/request |
| 001-00001-00001 | — | システム | 日次レポートの作成 | 対象日をキーに日次レポートを保存する。同じ対象日の再実行でもレポートを重複作成しない。 | — | — | w.daily_report/b.daily_report/p.daily_report/s.create_report |
| 001-00001-00002 | — | システム | 結果返却 | 終了コードとメッセージを返す。 | 出力：終了コード・メッセージ | 保持：日次レポート | w.daily_report/b.daily_report/p.daily_report/response |

## 型付き契約

| 固定ID | 名前 | コード上のキー | Python型 |
| --- | --- | --- | --- |
| a.report_date | 集計対象日 | business_date | str |
| a.report | 日次レポート | report | str |

## 起動定義の対応

| トリガー固定ID | 配置 | パイプライン | 許可ロール |
| --- | --- | --- | --- |
| t.daily_cron | b.daily_report | p.daily_report | role.report_system |

## 実装対応

| 固定ID | 実装 |
| --- | --- |
| s.create_report | examples.feature_demos.cron_reporting.application.create_report |

ロックはEngine → LockProvider、受付認可はEngine → Principal.rolesで実行。
