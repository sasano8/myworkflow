# バリューオブジェクトとデータ定義

## 正本と出力

Pydantic 2.12.5を標準依存として使う。バリューオブジェクトは値の意味・制約を定義し、固定IDで業務上の概念を識別する。Pythonのモデルクラスを参照するため、内部接続をモデル名の文字列で手書きしない。

```python
from pydantic import Field
from myworkflow import Artifact, ValueModel, ValueObject

class PurchaseAmount(ValueModel):
    yen: int = Field(gt=0, description="税込の購買申請金額。単位は円。", examples=[10000])

purchase_amount = ValueObject(
    "vo.purchase_amount", "購買申請金額", PurchaseAmount,
    description="円単位の正の整数。小数や文字列を受け付けない。",
)
amount = Artifact("a.amount", "申請金額", "amount", "dict", value_object=purchase_amount)
```

`ValueModel` はfrozen・未知項目拒否・strict・既定値検証を設定したBaseModel。通常のBaseModelを使う場合も、frozen・validate_defaultとextra='forbid'を設定する。単一値にはfrozen・validate_defaultを設定したRootModelを使える。[サンプル](../examples/approval_values/value_objects.py)の金額は整数のRootModelである。frozenはモデルの属性代入を制限するもので、内部のlist等まで深く不変にする保証ではない。

`Artifact.type` は正規化後のJSONデータの基本型で、`str / int / bool / float / dict` を指定する。バリューオブジェクトのSchemaのルート型と一致しなければコンパイルを拒否する。複合的なフィールド・任意項目・ネスト・配列はdictのモデル内部で表現できる。ルートが配列や複数型のUnionであるモデルを、現在のArtifact基本型へ対応させる機能はない。排他キーは引き続きスカラーに限定する。

アーティファクトから参照した定義は `compile_workflows` が収集する。保存レコード用や単独のデータ定義は `value_objects=(...)` に明示する。同じ固定IDで異なる定義オブジェクトを使うと拒否する。

```sh
python -m myworkflow build --config examples.approval_values.build \
  --target temporal --output dist/approval_values
python -m myworkflow build --config examples.approval_values.build \
  --target temporal --output dist/approval_values --check
```

定義があるビルドでは次を追加出力する。定義のない従来の契約の出力は維持する。

| ファイル | 内容 |
| --- | --- |
| `requirements.md` | 業務概要と、データ定義ファイルへの固定ID付き参照 |
| `data-definitions.md` | 名称・意味・必須項目・制約・既定値・例・補足ルールを簡易表で表示 |
| `data-definitions.json` | 同じ定義の機械可読形式、Python型、独自バリデーター、アーティファクト対応 |

[生成したデータ定義](../examples/approval_values/docs/data-definitions.md)と[業務概要](../examples/approval_values/docs/requirements.md)を別ファイルとして保存し、テストとCIで固定出力との一致を確認する。JSON Schemaは検証用の形式で出力し、入力の別名がある場合は正規の項目名とは別に記録する。build.jsonのハッシュ対象にも含める。

## 検証する境界

- パイプラインの入力、宣言されたステップの入出力、生成物として扱うアーティファクトを型定義で検証する。
- Contextには検証・正規化済みのJSONデータを渡す。入力はJSON形の値でも、該当するPydanticモデルのインスタンスでもよい。生成Requestの型注釈は元のモデルクラスを参照する。dataclass単体では検証せず、Engine通過時に検証する。
- `changes` では、型を結び付けたレコードを読込時と確定前に検証する。確定する状態も正規化後の値でトランジションと照合する。
- 任意のローカル変数でモデルを使うことは強制しない。フレームワーク外からの直接DB更新も保証しない。

モデルのインスタンスもJSONへ変換して再検証し、`model_construct` による検証省略を境界へ持ち越さない。JSONの厳密な検証なので、日付はISO形式の文字列として扱え、整数項目への文字列やbool等は拒否する。検証で補った既定値もContext・保存値へ反映する。PydanticオブジェクトそのものをDBへ保存したり、pickleを使用したりしない。

保存レコードの型はTransitionRuntimeへ明示的に接続する。

```python
transitions = TransitionRuntime(
    compiled, compiled.graphs[0], coordinator,
    key=lambda values: f"application:{values['application_id']}",
    value_object=approval_application,
)
```

`approval_application` はcompiled.catalogに含まれるValueObject。変更の書き方は従来通りである。

```python
application = ctx.changes.subject
ctx.changes.update(application, approved_by=ctx.actor, status=Approval.approved.id)
```

他の既存JSONレコードは `ctx.changes.read(key, value_object=delivery_period)` のように型を指定できる。同じレコードの型を読込み後に切り替えることは拒否する。型を結び付けていないレコードを自動推論して検証はしない。

型の検証が失敗した場合はprepare前に拒否し、変更を一件も確定しない。その後の楽観ロックと一括確定の保証は[トランジション実行](transition-execution.md)に従う。

## 条件の役割

バリューオブジェクトは「金額が正の整数」「終了日が開始日以降」等の値の正しさを担う。ガードは「現在承認待ち」「申請者本人ではない」等の操作可否を担い、楽観ロックは判断後の同時更新を検出する。

範囲・形式・必須項目等はJSON Schemaから出力できる。一方、`model_validator` 等の任意のPython処理、動的既定値、外部情報を参照する条件の意味はSchemaだけでは完全に表せない。バリデーターは副作用のない決定的な検証とする。ネスト先にも既定値検証等の適切なモデル設定が必要で、任意のPythonで検証を無効化するコードを封じる仕組みではない。独自バリデーターの名前はネスト先も含めて出力し、意味は `ValueObject.rules` と受入テストで補う。説明とコードの意味の一致を自動証明する機能ではない。納品期間の例では、日付形式はSchema、前後関係は補足ルールと実行テストで確認する。

機械可読の業務出力とIRにも定義・参照を含める。旧辞書SPECからモデルを再接続するときは `Program(spec, value_objects=definitions)` が必要で、Schema・メタデータがPython定義と一致することを確認する。外部ドキュメントに記載されたPythonパスを勝手にimportしない。JSON Schemaから任意の独自バリデーターを復元・自動生成する機能は残課題である。

既存の購買往復評価を、この追加によって意味の完全一致や全要件の構造化を達成したとは扱わない。状態遷移・データ定義を含む総合的な往復指標、実案件レビュー、外部サービスを含む確定、保持期限・GCは引き続き残課題。


## 購買サンプルの出力先

購買の正本は [purchase/value_objects.py](../examples/purchase/value_objects.py) に置き、contract.pyの申請ID・取引先・金額のArtifactから参照する。購買自身のContractCatalogへ含め、入力検証・生成Request・業務概要・ビルドに同じ定義を使う。

- [購買のデータ定義](../examples/purchase/docs/data-definitions.md)（[JSON](../examples/purchase/docs/data-definitions.json)）。
- [購買の業務概要](../examples/purchase/docs/requirements.md)。

```sh
python -m myworkflow build --config examples.purchase.build --target temporal --output dist/purchase
```

既存の検証と一致するよう、金額は正の整数、取引先は空文字・空白のみを拒否する。通貨・税区分、申請IDの書式等の未定義な制約を補ってはいない。申請ID等の未確定部分はデータ定義にも記載する。他の項目は基本型のままで、保存先Repositoryをchangesへ移行したものではない。

承認・バリューオブジェクト例は、納品期間の独自検証や確定前検証を示す追加サンプルとして維持する。購買の固定原文・変換結果を使う往復評価は従来の独立した基準を維持し、今回のデータ定義全体を採点済みとは扱わない。

バリューオブジェクトの生成Markdownは1項目1行の一覧表とし、定義ID・項目名・型・必須・説明・制約・既定値・例を横に並べる。完全なJSON SchemaはJSONファイルだけに出力する。[pre-commitでの自動生成](generated-documents.md)は、この別ファイル出力も更新してコミットへ含める。
