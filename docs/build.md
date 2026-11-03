# ビルド

Pythonの宣言を正本とし、型付きモデルから概要・型・比較用IRを生成します。IRやKestra YAMLを手書きの正本にはしません。

```sh
python -m myworkflow build --config examples.apps.purchase.build --target temporal --output dist/temporal
python -m myworkflow build --config examples.apps.purchase.build --target kestra --workflow w.attach --output dist/kestra
```

`--check` は書込みなしで一致を検査します。`--workflow` は複数指定でき、省略時は全体です。未選択の引継ぎ先はエラーとし、手書き呼出しから依存を推測しません。インストール後の `myworkflow build` と `python -m myworkflow.build` も同じ入口です。[設定例](../examples/apps/purchase/build.py)。

| 出力 | 内容 |
| --- | --- |
| ir.json | schema_version=1。業務形式v2、ハンドラーの入出力契約、状態グラフ、終了結果、実装対応 |
| requirements.md | 概要・実装対応。状態宣言があれば図と表も含む |
| interfaces.py | Requestと共通Responseの別名 |
| data-definitions.md / .json | ValueObjectがある場合の別ファイル出力 |
| build.json | 出力先・選択範囲・生成物のSHA256 |
| manifest.yaml | Kestra選択時の説明用プレビュー |

出力は時刻・絶対パスを含めず決定的です。手書きソースへの上書きを拒否します。モジュールのimportは通常のPythonとして実行されますが、ビルダーが宣言を発見するために業務ハンドラーを呼ぶことはありません。

## 出力先の対応範囲

Temporalはアプリ側のコードを維持し、ビルドで共通出力と実装接続を検査します。SDKは不要です。待機・再生・冪等性の静的証明や、状態グラフからのWorkflow生成はしません。

Kestraは `deployable: false` の独自YAMLで、そのまま配備できません。配置・トリガーごとのロール、入力対応、Pythonパイプラインの呼出し先を示します。ステップの分岐・再試行・補償はPython Engineが担当します。

`wait`・`after`・次ワークフロー・状態グラフ・未知のrequired_featuresは、未対応として固定ID付きでビルド失敗にします。現在のrequired_featuresはpython_pipelineのみです。Kestra自体の能力の限界という判定ではありません。購買全体は失敗し、明示したw.attachだけの部分ビルドは成功します。

Temporal用出力先に古いKestraマニフェストが残っていれば、混入を防ぐため失敗します。手書きコードは削除しません。配備可能な変換と実機検証は[残課題](poc-plan.md)、保存済み出力の更新は[pre-commit](generated-documents.md)を参照してください。
