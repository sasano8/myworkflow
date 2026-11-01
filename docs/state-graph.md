# 状態・遷移の宣言モデル

## クラス宣言からのコンパイル

実験用APIを `myworkflow.declarations` に追加した。承認・差戻し・再申請・却下を含む[宣言例](../examples/declarative_review.py)と、その[生成結果](../examples/declarative_review/docs/requirements.md)を参照できる。

```python
from myworkflow.declarations import workflow, state, trigger, bind, transition, compile_workflows

# reviewer / system は Role、review_pipeline は既存の Pipeline オブジェクト。
# 以下は入力を持たないパイプラインを配置する場合の例。
@workflow(id="w.review", name="申請審査")
class Review:
    pending = state("state.pending", "承認待ち", initial=True)
    approved = state("state.approved", "承認済み")
    approval = trigger("t.approval", "承認操作", reviewer)
    review = bind("b.review", review_pipeline, (approval,), (("system", system),))
    approve = transition("tr.approve", "承認", pending, approved, review, approval)

compiled = compile_workflows(Review, artifacts=())
program = compiled.program
catalog = compiled.catalog
state_graph = compiled.graphs[0]
```

`@workflow` はクラスを保つ。`Review.pending` や `Review.review` は通常のPython属性として参照できる。宣言はfrozen dataclassで、参照にはオブジェクトを渡す。初期状態は `initial=True` を一つだけ指定する。名前の変更に固定IDの変更は不要である。

`compile_workflows` は選択したクラスの属性を定義順に列挙し、`Program.from_catalog` に既存の型付きモデルを直接渡す。メソッド、プロパティ、業務ハンドラを呼び出して定義を発見することはない。ただし、通常のPythonなのでモジュールのimportやクラス本体の評価は実行される。任意のPythonソースを実行せず解析するツールではない。

トリガーの入力対応は `((artifact_object, "入力元の項目名"), ...)`、配置のロール対応は `(("抽象ロール枠", role_object), ...)` とする。ロール枠・入力元は外部との契約名である。配置の `next_workflow` は同時にコンパイルする別の宣言クラス、トリガーの `after` は同じワークフロー内の先行配置を参照する。複数トリガーと別配置でのパイプライン流用を維持する。

状態宣言のないワークフロークラスも利用でき、その場合は状態グラフを生成しない。状態を宣言する場合は初期状態を一つだけ指定する。

現段階では継承と、一つの状態・配置・遷移に複数のクラス属性名を付ける別名定義を拒否する。初期状態・所属・参照の曖昧さを避けるための暫定制約である。コンパイル後は宣言クラスを変更しても結果に追従せず、変更を反映するには再コンパイルする。

購買は `PipelineDeclaration`・`Action`・`Mutex`・`Operation` へ移行し、入力・成果物・読書き・条件・補償もオブジェクトで接続する。既存の `Pipeline`・`Step` は互換の中間モデルとして維持し、コンパイル時に固定IDへ変換する。[正本とビルド](build.md)を参照。アーティファクト一覧は `artifacts=(...)` で明示し、入力対応で同じIDを持つ別オブジェクトを渡した場合は拒否する。

既存の文書生成、`interfaces_source`、`skeleton_source`、`Engine` はコンパイル済み `Program` を使用できる。`program.spec` は互換用の辞書スナップショットであり、クラス宣言の正本ではない。ロックの範囲・操作ロールを含む互換出力の読込みも検証する。

このサンプルは契約の宣言例であり、審査の永続化を実装したアプリケーションではない。テストでは一時的なハンドラを接続し、生成した型付きインターフェースとパイプライン呼出し・起動ロール検査の接続を確認する。自然言語の条件の意味や状態更新は検証しない。

```sh
python -m examples.declarative_review
python -m pytest tests/test_declarations.py tests/test_state_graph.py -q
```

## 業務フロー図の生成

`myworkflow.flowchart.render_business_flow(graph, catalog)` は、同じ状態・遷移の宣言からMermaidのフローチャートを含むMarkdownを生成する。GitHubで閲覧できる[図の出力例](../examples/declarative_review/docs/flow.md)を用意した。通常の[概要出力](../examples/declarative_review/docs/requirements.md)にも図を含む。

```sh
python -m examples.declarative_review --flowchart
```

状態と操作を別のノードとし、操作に実行者とトリガーを記載する。「現在の状態 → 操作 → 成功後の状態」の接続を宣言から生成するため、差戻し・再申請の循環も表現できる。操作番号は状態遷移表の連番に対応する。

標準表示は概要とし、条件と対応パイプラインは隣接する表で確認する。`render_business_flow(graph, catalog, details=True)` では、図にも条件の説明とパイプライン名を表示できる。入出力・アーティファクト操作・ステップ内部の詳細は既存のパイプライン表に残す。

図は業務宣言上の成功経路を表す。未定義の失敗経路や終端状態を推測して補わない。状態グラフを持たない既存の購買契約を、実行履歴や説明文から推測して図に変換する機能ではない。図だけでは遷移を実行・保存しない。明示的に接続した[TransitionRuntime](transition-execution.md)では、限定した実行と一括確定ができる。

生成するノード名は内部の連番とし、業務名や固定IDを構文として挿入しない。ラベルの引用符、改行、Markdownコードフェンス等をエスケープする。固定出力との一致・循環・参照不正・ラベルを検査し、CIでも図の保存済み出力との一致を確認する。

## 中間モデルの実装

`myworkflow.state_graph` は、クラス宣言構文から独立した中間モデルである。`ContractCatalog` と組み合わせて使い、状態を宣言したクラスから生成する。購買の正本はクラス形式へ移行済みだが、購買の状態グラフの宣言と実行への接続は残課題である。

- `State` は固定IDと業務上の名前を持つ。
- `Transition` は現在の状態、成功後の状態、既存の配置 `Binding`、その配置の `Trigger` をオブジェクトで参照する。条件の概要も記載できる。
- `StateGraph` は既存のワークフロー、初期状態、全状態・遷移を列挙する。業務処理を実行せず検査・出力できる。
- 差戻し・再申請の循環と自己遷移を許す。固定IDの衝突、別ワークフローの配置、未宣言の状態、配置に属さないトリガー、初期状態から到達できない状態は拒否する。
- `to_dict(catalog)` はオブジェクト参照を固定IDへ変換した比較用データを返す。JSONからの逆変換は未実装。
- `render_state_graph(graph, catalog)` は「実行者 → トリガー → 現在の状態 → 成功後の状態」の順で表を生成する。実行者・パイプライン名は既存の契約から取得し、転記しない。

参照の検査は同じIDのコピーを正規の宣言と取り違えないよう、状態・配置・ワークフローについてオブジェクトの同一性を使う。トリガーは既存の `Binding.triggers` が値を生成するAPIなので値で対応させる。

現在の状態とは、遷移を試みられる前提の状態を指す。実行中インスタンスの現在値や履歴を出力する機能ではない。成功後の状態も宣言上の約束であり、このモデル単体でDB更新を保証しない。

## 宣言と実行の境界

`condition` は概要文字列であり、それ自体を実行しない。実行には別の `guard` 関数を接続する。TransitionRuntimeは開始状態とイベントに一致する候補のガードを評価し、適格な遷移がちょうど一つのときだけ進む。条件文があるのにガードがない場合、アダプターの構築を拒否する。グラフ単体で実行計画や待機処理を自動構築する機能ではない。

パイプラインは再利用する処理単位として維持する。具体的な業務状態は配置を参照する遷移側に置く。状態グラフのテストは宣言の整合性を検査するもので、申請者本人の確認や差戻し理由の保存など、実処理の受入テストを代替しない。

## 次の実装順序と完了条件

1. **ワークフロー層は実装済み**：名前付きクラス宣言をこのモデルと既存の `ContractCatalog` へコンパイルする。Pythonの識別子だけを変更する試験で、接続・固定ID・出力が維持されることを検証した。パイプライン・ステップ内部の参照と購買の正本も、その後オブジェクト参照へ移行済み。
2. **ローカルEngineで実装済み**：遷移の条件をguard関数へ対応付け、不一致・複数一致を拒否する。
3. 失敗時の扱いを、開始前の拒否・処理失敗・補償成功・補償失敗・結果不明に分けて決める。単に元の状態へ戻すと、外部副作用の残存を隠すため、既定の動作にはしない。
4. **ローカルCoordinator内は実装済み**：ctx.changesの業務項目と状態を同一トランザクションで確定し、応答消失・並行遷移の競合を試験した。外部I/Oは別途、実行ID・冪等性・復旧記録を含む方式を設計する。
5. Temporalへ同じ宣言を接続する。Signal・Timerをトリガーへ対応させ、Activity結果と永続化済み状態を照合する。再生・重複イベント・Activity完了通知消失・履歴変更時の対応を検証する。Temporal側の状態変数だけで業務DBの確定を推測しない。
6. クラス形式へ移行した購買サンプルへ状態・遷移を宣言し、正規化出力と往復品質検査へ追加する。承認、差戻し、再申請、却下、失敗を受入シナリオで確認する。独立した期待値をレビューし、既存の未表現要件を宣言追加だけで解消扱いにしない。

前段階のモデル・出力ができたことと、実行時の整合性・Temporal対応ができたことは別に評価する。
