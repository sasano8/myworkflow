# テスト

ディレクトリはmyworkflowのパッケージに対応し、業務サンプルの受入テストはapps、依存方向はarchitectureで検証します。

```sh
python -m pytest -q

# SDKとCLIを用意した場合、時間・対話を含む結合テストも実行
RUN_TEMPORAL_ACCEPTANCE=1 TEMPORAL_CLI_PATH=/path/to/temporal python -m pytest -q
```

SDKがなければTemporalテストを、CLIがなければ実サーバーテストを収集しません。BDD未導入時のコア検証はCIのcoreジョブと同じ対象を指定します。サンプル全体の文書生成にはacceptance依存が必要です。

原文・採点用期待値は自動更新しません。出力一致と業務上の正しさは独立して検証します。
