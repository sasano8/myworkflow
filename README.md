# myworkflow

**コードから、いつでも再現できる業務要件定義書。**

Python 3.14向けの、業務契約からインターフェース・実装骨格・業務概要を生成し、同じ契約でパイプラインを実行するPoCです。Pydanticを標準依存とし、Temporal接続は任意です。

## コンセプト

顧客の業務フローをPythonの宣言へ取り込み、生成した概要で合意します。開発へ移行した後はコードを正本とし、新しい要件もコードと受入シナリオへ反映します。概要から実装全体を復元することは目指しません。

| 概念 | 役割 |
| --- | --- |
| ワークフロー | 人の操作・待機・引継ぎを含む意味のある業務のまとまり |
| ハンドラー | 外部の入出力契約とパイプラインを接続する |
| パイプライン | 入力と処理順序を定義する再利用単位。終了コード・メッセージを返す |
| ステップ | Contextを受け取る処理。読書き、分岐、再試行、補償を宣言する |
| Binding・Trigger | 業務内への配置と起動条件。入力元・実行ロールを処理本体から分離する |
| アーティファクト・ValueObject | 扱う情報の識別と、値の意味・型・制約 |
| 状態・トランジション | 操作できる現在の状態と、成功後の状態。循環も表現できる |

`@role`・`@artifact`・`@step`・`@pipeline`・`@workflow`などの注釈で関数・クラスの `__myworkflow__` に型付き宣言を持たせ、独自属性と出力器を追加できます。[注釈と拡張](docs/annotations.md)。

宣言は業務契約カタログ（ContractCatalog）と状態グラフへコンパイルします。Pythonの参照で接続し、固定IDで改名後も追跡します。概要は全体像、Gherkinの受入シナリオは具体的な条件、実装は処理の詳細を担います。説明文だけで実行保証を主張せず、意味の妥当性はレビューとテストで確認します。

## 開発環境の構築

```sh
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test,acceptance]'
sh scripts/install-hooks.sh
python -m scripts.generate_docs --check
python -m pytest -q
```

新しいcloneごとにpre-commit hookをインストールしてください。[部分コミット・既存hookとの接続](docs/generated-documents.md)。Temporalは[任意の追加設定](docs/temporal.md)です。

## 試す

```sh
python -m examples.apps.purchase
python -m myworkflow build --config examples.apps.purchase.build --target temporal --output dist/purchase
```

[業務アプリと機能検証のサンプル一覧](examples/README.md)から、コードと各カタログの生成docsへ進めます。購買は申請・見積添付・承認・発注確定、チケット発行は独立した第二の業務例です。

## ドキュメント

| 目的 | 参照先 |
| --- | --- |
| 開発工程・正本の移行 | [工程図](docs/development-process.md) |
| 依存方向・公開入口 | [構成](docs/architecture.md) |
| 宣言・状態表・業務フロー図 | [状態グラフ](docs/state-graph.md) |
| 値の制約と出力 | [ValueObject](docs/value-objects.md) |
| 実行・終了結果・確定 | [接続層](docs/handlers.md)・[実行保証](docs/execution-design.md)・[終了結果](docs/pipeline-results.md)・[遷移実行](docs/transition-execution.md) |
| 保存・楽観ロック・保持方針 | [アーティファクト](docs/artifact-jobs.md) |
| 生成・ビルド | [pre-commit](docs/generated-documents.md)・[ビルド](docs/build.md) |
| 継続品質・評価 | [コード統計](docs/quality/README.md)・[往復品質](docs/requirements-quality.md)・[受入評価](docs/acceptance-evaluation.md)・[PoC評価](docs/poc-evaluation.md) |
| 継続判断 | [ゴールと残課題](docs/poc-plan.md)・[製品比較](docs/product-comparison.md) |

Kestra出力は説明用YAMLで、配備できません。本番認証・分散排他・外部副作用を含む一括確定は残課題です。
