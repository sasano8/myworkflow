# バリューオブジェクトとデータ定義

[購買の定義コード](../examples/apps/purchase/value_objects.py)を正本とし、[生成データ定義](../examples/apps/purchase/docs/data-definitions.md)を業務概要とは別に出力します。意味・単位・制約・未確定事項を明示し、実装の全変数でのクラス利用は強制しません。

## 定義と出力

ValueObjectはPydanticモデルへ固定ID・業務名・説明・補足ルールを結び付けます。Artifactから参照した定義は自動収集し、保存レコード等の単独定義は `value_objects=(...)` に指定します。同じIDの別オブジェクトは拒否します。

`ValueModel` はfrozen・extra拒否・strict・既定値検証を設定します。通常のBaseModelもfrozen・validate_default・extra='forbid'が必要です。RootModelにはfrozen・validate_defaultが必要です。ネスト先のモデルにも適切な設定を行ってください。frozenは内部list等の深い不変性を保証しません。

Artifactの基本型は `str / int / bool / float / dict` で、モデルのJSONルート型と照合します。ルート配列・複数型Unionは未対応です。ネスト・任意項目・配列はdictモデル内に表現でき、排他キーはスカラーに限定します。

| 出力 | 表現 |
| --- | --- |
| data-definitions.md | 1項目1行。定義ID・項目名・型・必須・説明・制約・既定値・例。ネストはパス表記 |
| data-definitions.json | 完全なSchema、Python型、独自検証名、入力別名、Artifact対応 |
| 業務概要・IR・Request | 固定IDの参照、Schema、元のモデル型を接続 |

任意のPythonバリデーターの意味・動的既定値はSchemaだけでは完全に表せません。副作用のない決定的な検証とし、意味は `rules` と受入テストで補います。意味の一致は自動証明しません。

## 検証する境界

Engineでパイプライン入力・ステップの読書き・成果物を検証します。Contextには正規化済みJSONを渡し、既定値も反映します。モデルのインスタンスも再検証し、`model_construct` の検証省略を引き継ぎません。Requestのdataclass単体では検証しません。

changesのレコードは明示的に型を指定した場合、読込みと確定前に検証します。同じレコードの型の途中変更は拒否します。型不正はprepare前に拒否し、正規化後の状態をトランジションと照合します。[接続例](../examples/feature_demos/approval_values/application.py)。

旧辞書を読む場合は `Program(spec, value_objects=definitions)` へ一致するPython定義を渡します。文書のPythonパスを動的importしません。型制約は値の正しさ、ガードは操作可否、楽観ロックは判断後の競合を担います。

購買の通貨・税区分・申請ID書式等の未定義な制約は補っていません。Repositoryをchangesへ移行したものでもありません。総合往復指標・型生成支援は[残課題](poc-plan.md)です。
