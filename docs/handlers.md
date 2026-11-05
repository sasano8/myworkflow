# 受付・結果返却のハンドラー

暗黙の「受付」「結果返却」を、一つのHandlerContractとして扱います。既存のBinding・Trigger・Pipelineへの参照から導出し、入力・ロール・応答有無を二重定義しません。

| 部品 | 責務 |
| --- | --- |
| HandlerContract | 起動定義・入力対応・成果物・応答契約を結ぶ読取り専用のビュー |
| Handler | 受付ロール・入力元を検査してContext用の値へ変換し、終了結果を外部応答へ接続 |
| Pipeline | Context上でステップを束ねて実行。排他・再試行・補償・接続した遷移契約を扱う |
| Step / StepDeclaration | 個々の処理と、そのPython参照による宣言 |

HandlerはPipelineを呼ぶ合成で、共通の実行基底クラスは設けません。注釈に必要な共通属性・拡張属性はExtensibleを利用します。

```python
# engineと、認証済み入口で構築したprincipalを使用する。
handler = engine.handler("b.submit", "t.submit")
response = handler.handle(
    {"id": "purchase-001", "vendor": "取引先", "amount": 100},
    principal,
    run_id="submit-001",
    respond=lambda result: (result.to_dict(), 200 if result.ok else 400),
)
```

respondは実行環境に合わせる変換関数です。既定は終了コード・メッセージの辞書で、HTTPステータス等をコアで決めません。成果アーティファクトはレスポンス項目に混ぜません。本人認証とPrincipalの構築は呼出し側の責務です。

`handler.invoke`は通常の失敗をPipelineResultへ変換し、`invoke_or_raise`は例外を伝播します。Engineの同名APIもこの接続層を通り、既存の呼出しを維持します。内部実行のrun_internalは受付を経由しません。

reply=Falseなら、handleは外部の業務応答を返さず、respondも呼びません。invokeは内部の終了結果を返し、実行履歴も保持します。通信上のACKは接続先で扱います。handleは同期呼出しで、応答不要の宣言だけではバックグラウンド実行になりません。

業務要件の「受付」「結果返却」は同じ契約ビューから生成し、既存の行・固定ID・応答不要の表示を保ちます。ビルドのir.jsonにもhandlersを出力します。宣言には[専用構文と共通の注釈](annotations.md)を利用できます。
