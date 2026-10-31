# Temporalの任意実行

Python 3.14.8、temporalio 1.35.0、Temporal CLI 1.9.1（Server 1.32.0）で確認済み。Temporal Cloudは不要です。

## 起動・停止

リポジトリ直下で実行します。サーバーとWorkerはテストが起動・停止します。常駐不要です。

```sh
uv venv --python 3.14
uv pip install 'temporalio==1.35.0'
bash scripts/install-temporal-cli.sh /tmp/myworkflow-temporal
TEMPORAL_CLI_PATH=/tmp/myworkflow-temporal/temporal .venv/bin/python -m unittest discover -s integration -v
```

SDKは任意依存 `temporal` にも宣言しています。CLI取得ヘルパーはLinux x86_64用で、GitHub公式リリースのSHA256を照合します。他環境では公式CLIの絶対パスを `TEMPORAL_CLI_PATH` に指定します。

このクラウド環境では必要に応じて `UV_CACHE_DIR=/tmp/myworkflow-uv-cache` を指定します。今回のCLIは `/workspace/temporal-tools/temporal`、Python 3.14は `/workspace/.myworkflow-python` 配下、仮想環境はリポジトリの `.venv` です。

## 検証内容

`integration/test_purchase.py` は実行契約を同じEngineへ接続します。

- 申請・見積書登録・承認・発注確定のDB処理。
- 承認待ち中にWorkerを停止し、新しいWorkerによる履歴再生後に再開する。
- 重複Signalは最初の判断だけを採用し、発注は1件だけ。
- タイマーと、契約の引継ぎ先IDに一致する子ワークフロー。
- 却下時は子ワークフローも発注も作らない。
- 権限不足の承認は失敗し、発注しない。

`integration/test_temporal.py` は初回の接続実験2件です。合計5件。異常系のActivity失敗ログは期待した結果です。

通常のCIはTemporalを起動しません。Actionsの `contracts` → Run workflow で `temporal` を有効にした場合だけ結合テストを実行します。手動CIの実行結果が確認できたかどうかは評価レポートで区別します。

## 限界

開発サーバーはインメモリです。試験したのはWorkerの再作成で、Temporalサーバー自身の再起動ではありません。実時間の短いタイマーを使います。時間スキップ用サーバーの自動取得先 `temporal.download` は環境の通信ポリシーで拒否されたため使用していません。

認証した受付、実S3、分散ロック、Activity途中停止の完全復旧、承認期限切れは未対応／未検証です。詳細な遷移と補償の保証範囲は[実行設計](execution-design.md)に記載しています。

## 購買サンプルのpytest-bdd受入テスト

同じfeatureから文書とテストを得る仕組みを追加した。[受入テストの手順](acceptance-evaluation.md)を参照。`RUN_TEMPORAL_ACCEPTANCE=1` とCLIのパスを指定した場合だけ、Temporalの2ケースを追加実行する。通常は明示的にスキップされる。ローカルの絶対日時境界試験と、Temporalの短い実時間Timerの試験は区別している。
