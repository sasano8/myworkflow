# myworkflow

Python 3.14向けの、業務契約から型・実装の骨格・業務概要を生成し、同じ契約でパイプラインを実行するPoCです。標準機能は外部依存なし、Temporal接続は任意です。

## 工程と次のタスク

[要件定義から開発までの工程図](docs/development-process.md)と、[受入テストのタスク](docs/acceptance-plan.md)を整理しています。顧客フローを繰り返しコードへ反映して概要で合意し、開発移行後はコードと受入シナリオを正本として生成資料で確認します。購買サンプルでは、同じGherkinからシナリオ文書生成とpytest-bddによる実行を行えます。

[現在の構成と移行方法](docs/architecture.md)に、共通モデル、実行基盤のProtocol、ロック、保存、受入プラグインの境界をまとめています。

## 動く購買申請サンプル

リポジトリ直下で実行します。

```sh
python3.14 -m examples.purchase
python3.14 -m unittest discover -s tests -v
python3.14 -m examples.purchase --docs > /tmp/purchase.md
diff -u examples/purchase/requirements.md /tmp/purchase.md
```

[生成した業務概要・型・実装対応表](examples/purchase/requirements.md)で、実行者、複数トリガー、入出力、分岐、補償、固定IDを確認できます。

申請 → 見積書2件登録 → 承認 → 発注確定をSQLiteで実行します。却下、権限不足、発注条件未達、途中失敗と補償もテストします。サンプル実行は一時DBを使用し、終了時に削除します。実S3や本番の認証・分散ロックは使いません。

## 要件からコードへ、コードから概要へ

[初期の業務要件](docs/requirements/purchase.md)をAI・開発者が解釈した構造から、最初のコードを生成します。

```sh
python3.14 -m myworkflow.scaffold init docs/requirements/purchase-initial.json /tmp/purchase-scaffold
```

空のディレクトリに契約コード、型付きdataclass、未実装関数を作ります。既存の実装は上書きしません。自然言語の解釈・確認はAIと人が担当します。

移行後の正本は [contract.py](examples/purchase/contract.py) です。手書き処理は [handlers.py](examples/purchase/handlers.py) に固定IDで接続します。変更後は型と概要を再生成します。

```sh
python3.14 -m myworkflow.scaffold interfaces examples.purchase.contract examples/purchase/interfaces.py
python3.14 -m examples.purchase --docs > examples/purchase/requirements.md
python3.14 -m unittest discover -s tests -v
```

期待値の更新は差分をレビューして行います。テスト中には再生成しません。初期要件の記録は履歴として残し、移行後の契約へ手作業で追従させません。

## モデル

| 要素 | 責務 |
| --- | --- |
| Workflow | 業務のまとまり |
| Binding | パイプラインの配置・起動定義。共通処理と利用箇所を分離 |
| Trigger | 起動経路、操作ロール、入力元と契約の対応 |
| Pipeline | 入力・出力・応答有無、処理順序 |
| Step | 固定ID、業務概要、実装関数、参照／保持する情報、分岐・補償 |
| Artifact | 情報の固定ID、名前、コード上のキー、型 |
| Role | ロールの正式名と表示名 |

受付・返却は契約から表示用の行を生成します。入力と出力は1列、途中のアーティファクト操作は別列です。複数トリガーの受付行を分け、後続ステップを共通表示します。名前・順序が変わっても定義の固定IDは維持します。実行IDは定義IDと別に発行します。

概要はパイプラインごとに表を分け、固定IDも表に表示します。複雑な状態遷移や復旧手順は別文書と実装へ整理します。[初期の宣言専用サンプル](examples/approval.py)も互換性確認用に残しています。

## 購買フローの受入テスト

[業務概要と受入条件](examples/purchase/acceptance/business.md)、[受入シナリオ文書](examples/purchase/acceptance/acceptance.md)、[実装・評価・実行手順](docs/acceptance-evaluation.md)を参照してください。対象はフレームワークそのものではなく、購買サンプルの業務フローです。

```sh
python -m pip install -e '.[acceptance]'
python -m examples.purchase.acceptance docs --check
python -m pytest -q --acceptance-report artifacts/acceptance.json
python -m examples.purchase.acceptance report artifacts/acceptance.json > artifacts/acceptance.md
```

featureを正本とし、操作・検証関数をPythonで実装します。概要・シナリオ文書は自動生成し、テスト結果は別に出力します。通常はローカル12ケース、Temporalをオンにすると計14ケースを実行します。

## TemporalとCI

[Temporal実行手順](docs/temporal.md)に従い、必要なときだけ結合テスト用サーバーを起動できます。Temporalからも同じEngineを使います。承認待ち中のWorker再作成・履歴再生、重複Signal、タイマー、子ワークフロー、却下を試験します。

通常のCIはPython 3.14で型・契約・実処理・障害試験と出力一致を検証します。TemporalはGitHub Actionsの手動実行で `temporal` をオンにした場合だけ実行します。

## 別の業務への適用例

[チケット発行の業務概要](examples/tickets/acceptance/business.md)と[受入条件](examples/tickets/acceptance/acceptance.md)は購買の型・保存処理を使わない第二の例です。本体を業務名で分岐させず、同じ実行・生成・受入ツールを設定で利用します。

```sh
python -m myworkflow.acceptance --config examples.tickets.acceptance.catalog docs --check
python -m pytest tests/tickets -q
```

## 元要件と生成コードの往復品質

[継続品質検査](docs/requirements-quality.md)で、原文 → レビュー済み出力形式 → インターフェース生成 → コードから再出力 → 比較を自動化しています。[レポート例](examples/purchase/quality/quality-example.md)では、構造の一致率と、原文の構造化・概要文のみ・未表現を区別します。

```sh
python -m myworkflow.quality --case examples/purchase/quality/case.json --output artifacts/requirement-roundtrip
```

現在の変換は固定サンプルで、AIによる意味変換は未実装です。期待値をテスト中に作り直さず、欠損・余計な項目・型や順序の違いを検出します。

## 判断と限界

[PoC評価](docs/poc-evaluation.md)、[実行設計・保証範囲](docs/execution-design.md)、[ゴールとタスク](docs/poc-plan.md)を参照してください。表層の契約対応を検証するPoCであり、本番用のワークフロー製品としての完成を意味しません。
