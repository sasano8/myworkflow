# 共有定義

[ワークフロー一覧](workflows.md)

<a id="role.system"></a>
## role.system：チケット管理システム

システム

<a id="ticket.operator"></a>
## ticket.operator：窓口担当者

受付担当

<a id="ticket.number"></a>
## ticket.number：受付番号

キー：number／型：str

データ制約：[vo.ticket.number](data-definitions.md#vo.ticket.number)

<a id="ticket.receipt"></a>
## ticket.receipt：発行結果

キー：receipt／型：str

<a id="ticket.issue"></a>
## ticket.issue：チケット発行

入力：ticket.number

出力：ticket.receipt

応答：あり

<a id="ticket.lock"></a>
### ticket.lock：受付番号の排他

排他キー：ticket.number。範囲：パイプライン終了まで（異常終了を含む）。競合時：拒否。名前空間：business。最大待機：0秒。

実行ロール枠：system

参照：ticket.number

生成：なし

操作：なし

<a id="ticket.save"></a>
### ticket.save：チケット保存

受付番号を重複なく登録し、発行結果を返す。

実行ロール枠：system

参照：ticket.number

生成：ticket.receipt

操作：DB作成：ticket.number、保持：ticket.receipt
