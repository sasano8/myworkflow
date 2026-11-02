# 状態・遷移の宣言

[宣言コード](../examples/feature_demos/declarative_review/contract.py)と[生成概要](../examples/feature_demos/declarative_review/docs/requirements.md)を参照してください。[共通の注釈プロトコル](annotations.md)を使ってパイプラインを配置し、その配置・トリガーを状態間のトランジションへ結び付けます。

```sh
python -m examples.feature_demos.declarative_review
python -m examples.feature_demos.declarative_review --flowchart
```

- 状態を持つワークフローの初期状態は一つです。状態なしの宣言も利用できます。
- 循環・自己遷移を許し、未到達状態・ID衝突・所属外の参照を拒否します。同じIDのコピーも正規の宣言として扱いません。
- 継承と同一宣言のクラス属性別名は、参照の曖昧さを避けるため拒否します。
- コンパイルで業務メソッドを実行しません。ただし通常のPythonのimport・クラス本体は評価されます。変更は再コンパイルで反映します。

表は「実行者 → トリガー → 現在の状態 → 成功後の状態」の順です。[Mermaid図](../examples/feature_demos/declarative_review/docs/flow.md)も同じ宣言から生成し、状態と操作を別ノードで表します。図の `details=True` は条件・パイプライン名も表示します。

現在の状態は操作の前提、成功後の状態は成功時の約束で、実行中の状態履歴ではありません。未定義の失敗経路は推測しません。`condition` の説明文と実行する `guard` 関数を区別し、実行・保存には[TransitionRuntime](transition-execution.md)を明示的に接続します。

状態宣言からTemporal/Kestraを自動構築する機能、JSONからの実行計画復元は未実装です。[残課題](poc-plan.md)。
