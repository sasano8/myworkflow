# Temporalの任意実行

[開発環境](../README.md#開発環境の構築)にSDKとCLIを追加します。Temporal Cloudや常駐サーバーは不要で、テストがサーバー・Workerを起動・停止します。

```sh
python -m pip install -e '.[test,temporal]'
bash scripts/install-temporal-cli.sh /tmp/myworkflow-temporal
TEMPORAL_CLI_PATH=/tmp/myworkflow-temporal/temporal python -m pytest tests/adapters/temporal -q

# BDDも含める場合（acceptance依存を導入済みの環境）
RUN_TEMPORAL_ACCEPTANCE=1 TEMPORAL_CLI_PATH=/tmp/myworkflow-temporal/temporal python -m pytest -q
```

SDKなしではTemporalテストを、CLI未指定では実サーバーの試験を収集しません。明示的に指定したCLIが使えなければ失敗します。BDDのTemporalケースはRUN_TEMPORAL_ACCEPTANCEで有効化し、通常はスキップします。

開発サーバーはインメモリです。Worker再作成の試験をサーバー再起動の保証とは扱いません。短い実時間Timerを使い、時間スキップ用サーバーの自動取得は行いません。実行・再試行・復旧の範囲は[実行設計](execution-design.md)を参照してください。

GitHub Actionsは手動実行のtemporal入力を有効にした場合だけ起動します。リモートの結果確認は[残課題](poc-plan.md)です。
