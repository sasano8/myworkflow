# cronによる日次レポート：機能単位の技術検証

このディレクトリは宣言コードから自動生成する。変更は元のコード・受入シナリオへ反映する。

宣言コード：[contract.py](../contract.py)

[ワークフロー一覧から読む](workflows.md)

| ドキュメント | 内容 |
| --- | --- |
| [example.crontab](example.crontab) | Cronie用crontab例（未登録） |
| [requirements.md](requirements.md) | 業務要件・型・実装対応 |
| [schedules.md](schedules.md) | cron式・タイムゾーン・起動先の定義 |
| [shared-definitions.md](shared-definitions.md) | 処理・ロール・データの共有定義 |
| [workflows.md](workflows.md) | ワークフロー一覧・未配置の定義 |

## 手動で1回実行

リポジトリのルートから実行します。集計結果はサンプルの固定本文です。

```sh
.venv/bin/python -m examples.feature_demos.cron_reporting --database /tmp/myworkflow-daily-report.db --date 2030-04-01
```

`--date` を省略すると、定義したタイムゾーンの前日を対象にします。対象日を主キーに保存するため、同じ日の再実行でもレポートは1件です。実行履歴は起動ごとに記録します。

## 定期実行

[example.crontab](example.crontab) はCRON_TZをサポートするCronie向けの例です。式とタイムゾーンはスケジュール定義から生成します。配置先 `/opt/myworkflow` とDB保存先を環境に合わせて変更し、外部のcronへ登録してください。このサンプルの生成・テストでは登録しません。

cronが停止していた期間の追いつき実行は自動化しません。必要な対象日を `--date` で指定して再実行します。DB書込みが競合・失敗した場合はコマンドが失敗します。分散ロックや通知はこの例の対象外です。
