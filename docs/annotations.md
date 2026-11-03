# 注釈と拡張

専用構文は `@step`・`@pipeline`・`@workflow` です。内部では型付き宣言を作り、共通の `対象.__myworkflow__` へ取り付けます。関数のラップや実行方式の変更は行いません。

| 構文 | 保持する宣言 | 対象 |
| --- | --- | --- |
| @step(...) | StepDeclaration | ステップの処理関数 |
| @pipeline(...) | PipelineDeclaration | stepsで構成を示す関数 |
| @workflow(...) | WorkflowDeclaration | 名前付き属性を持つクラス、またはmembersを指定した関数 |

IDは必須です。省略した名前には関数名・クラス名、ステップの概要にはdocstringを使います。各宣言と同じ標準属性とextensionsを指定できます。

```python
from myworkflow import step
from myworkflow.runtime import Context

@step(id='s.notify', extensions={'ui': {'label': '通知する'}})
def notify(ctx: Context) -> None:
    """処理状況を通知する。"""
    ctx.add_message('処理しました')

# @annotate(StepDeclaration(...)) と同じ宣言を保持する。
```

`annotate(宣言オブジェクト)`と直接代入も利用できます。`annotate` はIDを持つ独自クラスのインスタンスも扱えます。関数の引数・戻り値をコアで制限しません。標準の実行Registryへ接続するときにだけ `(ctx: Context) -> None` を検証します。

処理単位の宣言名はStepDeclaration、コンパイル後のモデル名はStepです。旧Action名は使用しません。既存のJSON形式にあるkind="action"は互換タグとして維持します。

## 宣言・接続・実行

- `declaration(target)` で注釈を読みます。既存の宣言オブジェクトを渡した場合は、そのまま返します。
- StepDeclaration・PipelineDeclaration等は型付き注釈として再利用します。StepDeclarationの名前・概要を省略した場合は、注釈先の関数名・docstringをコンパイル時に使います。
- パイプラインのstepsには注釈付き関数を参照できます。`registry.register(function)` で同じ関数を実装へ登録し、IDを転記しません。
- ワークフローは `@workflow(...)` を使います。クラスの名前付き属性、または関数に付けた `members=(...)` で状態・配置・遷移を列挙します。
- 宣言収集は関数本体を実行しません。標準Engineはパイプラインのstepsを実行し、注釈先のパイプライン／ワークフロー関数本体は呼びません。通常のPythonとして直接呼び出すことはできます。

[購買の処理関数](../examples/apps/purchase/handlers.py)は正本の宣言を参照して注釈を付け、定義後にRegistryへ登録します。生成骨格は同じ `annotate` とID参照の `Operation` を使い、未実装関数は成功扱いにしません。

[承認サンプル](../examples/feature_demos/approval_values/application.py)に、関数注釈と既存のクラス形式を組み合わせた例があります。実行・排他・補償・状態の保証は、接続した各機能の契約に従います。

## 拡張と出力

標準属性は各宣言クラスが型を定義します。独自情報は `extensions` へ、例えばcustomer・ui等の名前空間で追加します。コアは内容を解釈せず、コンパイル後も保持します。標準Markdownへ自動的に列を増やすことはありません。

Mappingと配列のコンテナは読取り専用にコピーします。任意のPythonオブジェクトは参照として保持し、その内部状態の不変性まで保証しません。JSONへ出せない値は黙って捨てず、出力時に失敗させます。

```python
BUILD = BuildConfig(
    compiled, registry,
    document_renderer=my_document,  # (program, graphs, registry) -> str
    extension_encoder=my_encoder,  # 独自値 -> JSON互換の値
)
```

独自出力器は型付きモデル・状態グラフ・拡張属性を直接参照できます。extension_encoderはJSON出力の境界だけで使い、元の注釈を書き換えません。業務JSON・IR・辞書スナップショットは拡張属性を保持します。JSONから任意のPythonオブジェクトを自動復元する機能はありません。
