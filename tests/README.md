# テスト構成

| ディレクトリ | 対象 |
| --- | --- |
| contracts | 契約モデル・状態・バリューオブジェクト |
| compiler | 宣言・入力形式・参照・データフロー検証 |
| runtime | 実行・型境界・遷移・再試行・補償・終了結果 |
| storage | 保存Protocolの契約。ローカルProviderを用いて検証 |
| adapters | ロック、Temporal接続等の実装 |
| generation | 文書・表・図・型・骨格・ファイル出力・hook |
| build | 生成物の組立て、未対応機能の拒否 |
| acceptance | 受入ツール・選択・レポートの振る舞い |
| quality | 元要件・生成コード・再出力の往復と欠損検出 |
| apps | 購買・チケットの業務サンプルに対するテスト |
| architecture | パッケージの依存方向と中核の独立性 |
| _support | テスト間で共有する宣言データの構築 |

```sh
# 標準のテストとBDD。Temporalの実サーバーは起動しない
python -m pytest tests -q

# TemporalのSDK・CLIを用意して、実サーバーと時間・対話のシナリオも実行
RUN_TEMPORAL_ACCEPTANCE=1 TEMPORAL_CLI_PATH=/path/to/temporal \
  python -m pytest tests -q
```

Temporal SDKがない場合はadapters/temporalのテストを収集しない。CLI未設定の場合は実サーバーのテストを収集しない。受入依存がないコア環境では、contracts・compiler・runtime・storage・generation・build・quality・adapters・architectureを指定する。generationのサンプル全体の出力検査は受入依存が必要なので、コア環境では対象外とする。

原文・採点用期待値は生成せず、出力一致と業務上の正しさは独立した検証として扱う。
