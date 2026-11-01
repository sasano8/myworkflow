# myworkflow

Python 3.14向けの、業務契約から型・実装の骨格・業務概要を生成し、同じ契約でパイプラインを実行するPoCです。データ契約にはPydanticを使用し、Temporal接続は任意です。

定義は業務契約カタログ（`ContractCatalog`）にまとめます。状態・トランジションは状態グラフとして合わせて管理します。[構成と名称](docs/architecture.md#業務契約カタログ)を参照してください。

## プロダクトの考え方と比較

[プロダクトの概念](docs/product-concept.md)に、業務契約、正本と生成物、要件定義から開発への流れ、現在の保証範囲を整理しています。[既存製品との比較](docs/product-comparison.md)では、n8n・Power Automate・Camunda・Windmill・SpiffWorkflow・Temporal・Prefectとの違い、強みと弱み、継続する価値を検証する条件をまとめています。

## 開発環境の構築

Python 3.14を用意し、リポジトリ直下で実行します。依存関係の導入に続けて、pre-commit hookもインストールします。

```sh
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test,acceptance]'
sh scripts/install-hooks.sh
python -m scripts.generate_docs --check
```

`install-hooks.sh` がGitのpre-commit hookを有効にします。新しいcloneごとに実行してください。既存hookとの接続方法やPython環境の指定は[hookの設定手順](docs/generated-documents.md#有効化)を参照してください。

## ライブラリとテストの構成

ソースは `contracts/`、`compiler/`、`runtime/`、`storage/`、`adapters/`、`generation/`、`build/`、`acceptance/`、`quality/` に責務を分けています。テストも同じ分類に対応させ、業務サンプルの受入テストは `tests/apps/` に置いています。[依存方向とAPI](docs/architecture.md#責務と依存方向)、[テスト構成](tests/README.md)を参照してください。

## サンプル構成

### 業務アプリのサンプル：`examples/apps/`

| アプリ | 内容 | ドキュメント |
| --- | --- | --- |
| `purchase` | 購買申請・見積添付・承認・発注確定を行うアプリ | [購買](examples/apps/purchase/docs/README.md) |
| `tickets` | 別の業務でも利用できることを確認する、独立したチケット発行アプリ | [チケット発行](examples/apps/tickets/docs/README.md) |

### 機能単位の技術検証：`examples/feature_demos/`

| 検証 | 対象機能 | ドキュメント |
| --- | --- | --- |
| `approval_values` | バリューオブジェクト、ガード、状態検証と楽観ロック付き確定 | [検証例](examples/feature_demos/approval_values/docs/README.md) |
| `declarative_review` | 状態・遷移の宣言、循環、表とフロー図の生成 | [検証例](examples/feature_demos/declarative_review/docs/README.md) |
| `prepared_approval` | アーティファクトの準備・一括確定・明示的な復旧 | [検証例](examples/feature_demos/prepared_approval/docs/README.md) |

業務アプリと機能検証は別々に動きます。[サンプル一覧](examples/README.md)を参照してください。各ディレクトリにコードと `docs/` をまとめ、生成するPythonの型定義はコード側へ置きます。

## コミット時の自動生成

`sh scripts/install-hooks.sh` でpre-commit hookを有効にすると、宣言から文書・型を再生成し、生成物を自動でコミットへ含めます。Python 3.14の `.venv` と `.[test,acceptance]` が必要です。[設定・対象・部分コミットの扱い](docs/generated-documents.md)を参照してください。

```sh
.venv/bin/python -m scripts.generate_docs         # 手動生成
.venv/bin/python -m scripts.generate_docs --check # 差分検査
```

## ビルド

購買の正本はPythonのクラス宣言です。型付きモデルから業務概要・型・中間表現を生成し、Kestra向けには説明用YAMLを出力します。未対応の待機・遷移等はビルド失敗になります。[使い方と対応範囲](docs/build.md)を参照してください。

```sh
python -m myworkflow build --config examples.apps.purchase.build --target temporal --output dist/temporal
python -m myworkflow build --config examples.apps.purchase.build --target kestra --workflow w.attach --output dist/kestra
```

Kestra出力は `deployable: false` のプレビューです。実機へ配備するFlow生成・実行アダプターは残課題です。

## 工程と次のタスク

[要件定義から開発までの工程図](docs/development-process.md)と、[受入テストのタスク](docs/acceptance-plan.md)を整理しています。顧客フローを繰り返しコードへ反映して概要で合意し、開発移行後はコードと受入シナリオを正本として生成資料で確認します。購買サンプルでは、同じGherkinからシナリオ文書生成とpytest-bddによる実行を行えます。

[現在の構成と移行方法](docs/architecture.md)に、共通モデル、実行基盤のProtocol、ロック、保存、受入プラグインの境界をまとめています。

## 名前付きクラス宣言の実験

[クラス宣言例](examples/feature_demos/declarative_review/contract.py)から、既存の型付き契約と状態グラフをコンパイルできます。[生成結果](examples/feature_demos/declarative_review/docs/requirements.md)には承認・差戻し・再申請・却下を出力します。[業務フロー図](examples/feature_demos/declarative_review/docs/flow.md)も同じ宣言からMermaid形式で生成し、GitHubで表示できます。`python -m examples.feature_demos.declarative_review --flowchart` で図だけ出力できます。`python -m examples.feature_demos.declarative_review` で再生成できます。構文・対応範囲・残タスクは[状態遷移モデル](docs/state-graph.md)を参照してください。ローカルでの遷移検証・確定は[TransitionRuntime](docs/transition-execution.md)を明示的に接続して行えます。この宣言例自体は審査を保存するアプリケーションではありません。

## 動く購買申請サンプル

上記の開発環境を構築した後、仮想環境を有効にしてリポジトリ直下で実行します。

```sh
python3.14 -m examples.apps.purchase
python3.14 -m pytest -q
python3.14 -m examples.apps.purchase --docs > /tmp/purchase.md
diff -u examples/apps/purchase/docs/requirements.md /tmp/purchase.md
```

[生成した業務概要・型・実装対応表](examples/apps/purchase/docs/requirements.md)で、実行者、複数トリガー、入出力、分岐、補償、固定IDを確認できます。

申請 → 見積書2件登録 → 承認 → 発注確定をSQLiteで実行します。却下、権限不足、発注条件未達、途中失敗と補償もテストします。サンプル実行は一時DBを使用し、終了時に削除します。実S3や本番の認証・分散ロックは使いません。

## 要件からコードへ、コードから概要へ

[初期の業務要件](docs/requirements/purchase.md)と解釈結果は履歴として保持しています。現在の共通終了結果を前提とした[回帰入力](docs/requirements/purchase-completion.md)と生成・比較は[継続品質検査](docs/requirements-quality.md)を参照してください。次のコマンドは初期入力の構造から現在の契約方式で骨格を生成するもので、旧レスポンス契約との意味の一致を保証しません。

```sh
python3.14 -m myworkflow.generation.scaffold init docs/requirements/purchase-initial.json /tmp/purchase-scaffold
```

空のディレクトリに契約コード、型付きdataclass、未実装関数を作ります。既存の実装は上書きしません。自然言語の解釈・確認はAIと人が担当します。

移行後の正本は [contract.py](examples/apps/purchase/contract.py) です。手書き処理は [handlers.py](examples/apps/purchase/handlers.py) に固定IDで接続します。変更後は型と概要を再生成します。

```sh
python3.14 -m myworkflow.generation.scaffold interfaces examples.apps.purchase.contract examples/apps/purchase/interfaces.py
python3.14 -m examples.apps.purchase --docs > examples/apps/purchase/docs/requirements.md
python3.14 -m pytest -q
```

期待値の更新は差分をレビューして行います。テスト中には再生成しません。初期要件の記録は履歴として残し、移行後の契約へ手作業で追従させません。

## パイプラインの終了結果

パイプラインは `PipelineResult(code, messages)` を返します。成功は0、コードのない例外は1。メッセージにはinfo・warning・error・criticalを付けられます。業務データはアーティファクトとして別に扱います。[例外・Temporal・生成型の契約](docs/pipeline-results.md)を参照してください。

## アーティファクトの準備と一括確定

[共通インターフェースと一時領域Provider](docs/artifact-jobs.md)を追加しました。ジョブIDで準備・確定・照会・破棄を管理し、同じSQLite内の業務データ・状態・ファイル参照をまとめて確定します。blob本体はジョブ別のファイルとして保存し、DBへ格納しません。`python -m examples.feature_demos.prepared_approval` で[承認例](examples/feature_demos/prepared_approval/application.py)を実行できます。外部DB等を含む一括確定は保証範囲外です。

## モデル

| 要素 | 責務 |
| --- | --- |
| Workflow | 業務のまとまり |
| Binding | パイプラインの配置・起動定義。共通処理と利用箇所を分離 |
| Trigger | 起動経路、操作ロール、入力元と契約の対応 |
| Pipeline | 入力・成果アーティファクト・終了結果・応答有無、処理順序 |
| Step | 固定ID、業務概要、実装関数、参照／保持する情報、分岐・補償 |
| Artifact | 情報の固定ID、名前、コード上のキー、型 |
| Role | ロールの正式名と表示名 |

受付・返却は契約から表示用の行を生成します。入力と出力は1列、途中のアーティファクト操作は別列です。複数トリガーの受付行を分け、後続ステップを共通表示します。名前・順序が変わっても定義の固定IDは維持します。実行IDは定義IDと別に発行します。

概要はパイプラインごとに表を分け、固定IDも表に表示します。複雑な状態遷移や復旧手順は別文書と実装へ整理します。購買業務の定義は `examples/apps/purchase/contract.py` に集約しています。宣言APIの単体試験にはテスト内の小さな汎用データを使います。

## 購買フローの受入テスト

[業務概要と受入条件](examples/apps/purchase/docs/business.md)、[受入シナリオ文書](examples/apps/purchase/docs/acceptance.md)、[実装・評価・実行手順](docs/acceptance-evaluation.md)を参照してください。対象はフレームワークそのものではなく、購買サンプルの業務フローです。

```sh
python -m pip install -e '.[acceptance]'
python -m examples.apps.purchase.acceptance docs --check
python -m pytest -q --acceptance-report artifacts/acceptance.json
python -m examples.apps.purchase.acceptance report artifacts/acceptance.json > artifacts/acceptance.md
```

featureを正本とし、操作・検証関数をPythonで実装します。概要・シナリオ文書は自動生成し、テスト結果は別に出力します。通常はローカル12ケース、Temporalをオンにすると計14ケースを実行します。

## TemporalとCI

[Temporal実行手順](docs/temporal.md)に従い、必要なときだけ結合テスト用サーバーを起動できます。Temporalからも同じEngineを使います。承認待ち中のWorker再作成・履歴再生、重複Signal、タイマー、子ワークフロー、却下を試験します。

通常のCIはPython 3.14で型・契約・実処理・障害試験と出力一致を検証します。TemporalはGitHub Actionsの手動実行で `temporal` をオンにした場合だけ実行します。

## 別の業務への適用例

[チケット発行の業務概要](examples/apps/tickets/docs/business.md)と[受入条件](examples/apps/tickets/docs/acceptance.md)は購買の型・保存処理を使わない第二の例です。本体を業務名で分岐させず、同じ実行・生成・受入ツールを設定で利用します。

```sh
python -m myworkflow.acceptance --config examples.apps.tickets.acceptance.catalog docs --check
python -m pytest tests/apps/tickets -q
```

## 元要件と生成コードの往復品質

[継続品質検査](docs/requirements-quality.md)で、原文 → レビュー済み出力形式 → インターフェース生成 → コードから再出力 → 比較を自動化しています。[レポート例](examples/apps/purchase/quality/quality-example.md)では、構造の一致率と、原文の構造化・概要文のみ・未表現を区別します。

```sh
python -m myworkflow.quality --case examples/apps/purchase/quality/case.json --output artifacts/requirement-roundtrip
```

現在の変換は固定サンプルで、AIによる意味変換は未実装です。期待値をテスト中に作り直さず、欠損・余計な項目・型や順序の違いを検出します。

## 判断と限界

[PoC評価](docs/poc-evaluation.md)、[実行設計・保証範囲](docs/execution-design.md)、[ゴールとタスク](docs/poc-plan.md)を参照してください。表層の契約対応を検証するPoCであり、本番用のワークフロー製品としての完成を意味しません。

### トランジション契約付きの更新

[実行サンプル](examples/feature_demos/approval_values/application.py)では `ctx.changes.update(application, approved_by=ctx.actor, status=Approval.approved.id)` を、開始状態・ロール・ガード・成功後の状態と照合し、最後に楽観ロック付きで一括確定する。[使い方と保存範囲](docs/transition-execution.md)を参照。

```sh
python -m examples.feature_demos.approval_values
```

### バリューオブジェクトと別ファイルのデータ定義

Pydanticモデルを固定ID付きの `ValueObject` として宣言し、入力と型を結び付けた更新を検証します。購買の[業務概要](examples/apps/purchase/docs/requirements.md)とは別に[データ定義](examples/apps/purchase/docs/data-definitions.md)を生成します。[定義コード](examples/apps/purchase/value_objects.py)は購買自身の業務契約カタログへ接続しています。[定義方法と保証範囲](docs/value-objects.md)を参照してください。

```sh
python -m myworkflow build --config examples.apps.purchase.build --target temporal --output dist/purchase
```
