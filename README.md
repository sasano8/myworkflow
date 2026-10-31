# myworkflow

Python 3.14向けの、業務契約から型・実装の骨格・業務概要を生成し、同じ契約でパイプラインを実行するPoCです。標準機能は外部依存なし、Temporal接続は任意です。

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

## TemporalとCI

[Temporal実行手順](docs/temporal.md)に従い、必要なときだけ結合テスト用サーバーを起動できます。Temporalからも同じEngineを使います。承認待ち中のWorker再作成・履歴再生、重複Signal、タイマー、子ワークフロー、却下を試験します。

通常のCIはPython 3.14で型・契約・実処理・障害試験と出力一致を検証します。TemporalはGitHub Actionsの手動実行で `temporal` をオンにした場合だけ実行します。

## 判断と限界

[PoC評価](docs/poc-evaluation.md)、[実行設計・保証範囲](docs/execution-design.md)、[ゴールとタスク](docs/poc-plan.md)を参照してください。表層の契約対応を検証するPoCであり、本番用のワークフロー製品としての完成を意味しません。
