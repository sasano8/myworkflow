# Temporal接続実験

Python 3.14.8、temporalio 1.35.0、Temporal CLI 1.9.1（Server 1.32.0）で確認済み。Temporal Cloudは不要です。

## 任意で実行する

リポジトリ直下で実行します。通常のテストとCIはTemporalを使いません。以下を実行したときだけ開発用サーバーとWorkerを起動し、終了時に停止します。

```sh
uv venv --python 3.14
uv pip install 'temporalio==1.35.0'
bash scripts/install-temporal-cli.sh /tmp/myworkflow-temporal
TEMPORAL_CLI_PATH=/tmp/myworkflow-temporal/temporal .venv/bin/python -m unittest discover -s integration -v
```

Pythonパッケージの任意依存は `pyproject.toml` の `temporal` に宣言しています。CLI取得ヘルパーはLinux x86_64用です。他環境では公式CLIをインストールし、実行ファイルの絶対パスを `TEMPORAL_CLI_PATH` に指定します。GitHub公式リリースのSHA256を照合し、TLS検証を無効化しません。

このクラウド環境ではuvの既定キャッシュへの書込みが制限されるため、必要に応じて `UV_CACHE_DIR=/tmp/myworkflow-uv-cache` を指定します。今回の環境ではCLIを `/workspace/temporal-tools/temporal` に配置しました。

## 確認したこと

- 実際のTemporalサーバーとWorkerで実行する。
- 承認前は待機し、子ワークフローがまだ開始されていないこと。
- Signalによる承認後、タイマーを経て子ワークフローを起動すること。
- 実行履歴にタイマーと、宣言にある `w.execution` の子ワークフロー起動が記録されること。
- 見積書がない場合はActivityが失敗すること。

テストは2件。異常系のActivity失敗ログは期待した結果です。CIへの組込みはまだ行いません。テストサーバーは都度起動するインメモリ構成で、再起動をまたぐ復元は未検証です。実時間の短いタイマーを使います。時間スキップ用サーバーの自動取得先 `temporal.download` は現在の通信ポリシーで拒否されたため使用していません。

## 契約との対応と限界

| 宣言ID | 実験コード |
| --- | --- |
| w.approval | ApprovePurchase |
| w.execution | ConfirmPurchase |
| s.confirm-order | confirm_order Activity |

`examples/temporal_purchase.py` は固定IDで対応付けた手書きの接続実験です。宣言全体からTemporalコードを生成するアダプタではありません。待機と遷移はこの別文書およびTemporal実装に整理しています。元のサンプルの全トリガー・ステップを実行してはいません。

発注確定は `confirmed-demo` を返すだけで、DBへの保存やトランザクションは未実装です。認可・排他・重複発注防止・本番用の入力型・承認Signalの利用者検証も未実装です。この実験をもって発注の業務契約全体の保証とはしません。

次はPoC計画のP0-02で実装対応方式を定め、手書きで重複している契約を解消します。Activityの分割と再試行境界、冪等性の設計もその際に検討します。
