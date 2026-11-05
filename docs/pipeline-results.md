# パイプラインの終了結果

`PipelineResult(code, messages)` を共通の戻り値とします。業務データはアーティファクトへ置きます。

```python
PipelineResult(code=0, messages=(Message(level="info", text="申請を受け付けました"),))
raise BusinessError(10, "発注条件を満たしていません", level="warning")
```

| 項目・原因 | 契約 |
| --- | --- |
| code | 非負のアプリケーション整数。0は成功、その他は失敗。HTTP・OS終了コードとは別 |
| messages | info / warning / error / criticalの文章列。空も可 |
| 明示コード付きPipelineError・BusinessError | 指定のコード・重大度・文章と、それ以前のメッセージを維持 |
| 通常の未分類例外 | 1とerror。PermissionError・ContractErrorも同じ |
| 補償・ロック解放・履歴保存の追加障害 | 1とcritical。元の原因も残す |

コードの大小は重大度を表しません。warning付きの成功も可能です。ステップは `(ctx: Context) -> None` とし、`ctx.add_message(text, level='info')` でメッセージを追加します。再試行・補償・解放を終えてから結果へ変換し、KeyboardInterrupt等のBaseExceptionは通常の失敗に変換しません。偶然存在する例外属性からコードを推測しません。

## 呼出しとアーティファクト

[ハンドラー](handlers.md)が受付と結果の接続を担います。`invoke` は受付認可付き、`run_internal`（互換名run）は内部用です。`invoke_or_raise`・`run_or_raise` は例外を伝播し、Temporal等の接続や障害試験で使います。成功時はいずれも同じPipelineResultです。

Pipeline.outputsは、完了時に存在・型を検査する成果物IDです。レスポンス項目ではなく、DB保存まで保証しません。後続処理へ渡す業務IDは入力・DB・ストレージ等から明示的に渡します。生成ResponseはPipelineResultの別名で、古い業務データ入りの型はEngine構築時に拒否します。

`reply=False` は受付へ業務応答を返さない宣言です。実行内部の終了結果と履歴は残ります。HTTPステータス・CLI終了コード・Temporal失敗への変換は実行環境のアダプターが担います。外部へ例外文をそのまま公開するかも受付側で判断します。

確定後に後処理が失敗する場合があるため、終了コードだけで未確定と判断せず、[ジョブ状態](artifact-jobs.md)を照会してください。
