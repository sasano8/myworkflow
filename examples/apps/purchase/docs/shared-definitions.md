# 共有定義

[ワークフロー一覧](workflows.md)

<a id="role.requester"></a>
## role.requester：購買依頼部門の担当者

申請者

<a id="role.approver"></a>
## role.approver：購買依頼部門の部門長

承認者

<a id="role.buyer"></a>
## role.buyer：購買部の発注担当者

発注担当者

<a id="role.system"></a>
## role.system：購買管理システム

システム

<a id="a.id"></a>
## a.id：購買申請ID

キー：application_id／型：str

データ制約：[vo.purchase.application_id](data-definitions.md#vo.purchase.application_id)

<a id="a.vendor"></a>
## a.vendor：取引先

キー：vendor／型：str

データ制約：[vo.purchase.vendor](data-definitions.md#vo.purchase.vendor)

<a id="a.amount"></a>
## a.amount：申請金額

キー：amount／型：int

データ制約：[vo.purchase.amount](data-definitions.md#vo.purchase.amount)

<a id="a.status"></a>
## a.status：申請状態

キー：status／型：str

<a id="a.quote-a"></a>
## a.quote-a：見積書A

キー：quote_a／型：str

<a id="a.quote-b"></a>
## a.quote-b：見積書B

キー：quote_b／型：str

<a id="a.receipt"></a>
## a.receipt：添付登録結果

キー：receipt／型：str

<a id="a.decision"></a>
## a.decision：承認判断

キー：decision／型：bool

<a id="a.eligible"></a>
## a.eligible：発注可能

キー：eligible／型：bool

<a id="a.order"></a>
## a.order：発注番号

キー：order_id／型：str

<a id="p.submit"></a>
## p.submit：購買申請受付

入力：a.id、a.vendor、a.amount

出力：a.id、a.status

応答：あり

<a id="s.submit-lock"></a>
### s.submit-lock：申請単位の排他

排他キー：a.id。範囲：パイプライン終了まで（異常終了を含む）。競合時：拒否。名前空間：business。最大待機：0秒。

実行ロール枠：system

参照：a.id

生成：なし

操作：なし

<a id="s.submit"></a>
### s.submit：申請保存

正の金額と取引先を確認し、申請者に紐づく承認待ちの申請を保存する。

実行ロール枠：system

参照：a.id、a.vendor、a.amount

生成：a.status

操作：DB作成：a.id、保持：a.status

<a id="p.upload"></a>
## p.upload：見積書2件登録

入力：a.id、a.quote-a、a.quote-b

出力：a.receipt

応答：あり

<a id="s.upload-lock"></a>
### s.upload-lock：申請単位の排他

排他キー：a.id。範囲：パイプライン終了まで（異常終了を含む）。競合時：拒否。名前空間：business。最大待機：0秒。

実行ロール枠：system

参照：a.id

生成：なし

操作：なし

<a id="s.check-upload"></a>
### s.check-upload：添付可否確認

申請者本人であり、申請が承認待ちであることを確認する。

実行ロール枠：system

参照：a.id

生成：なし

操作：なし

<a id="s.put-a"></a>
### s.put-a：見積書A保存

今回の実行専用キーで見積書Aを保存する。 失敗時の補償：c.delete-a（逆順、失敗した処理も対象）。 一時障害のみ最大2回試行。

実行ロール枠：system

参照：a.id、a.quote-a

生成：なし

操作：参照：a.quote-a

<a id="s.put-b"></a>
### s.put-b：見積書B保存

見積書Bを保存し、両方の添付情報を申請に紐づける。 失敗時の補償：c.delete-b（逆順、失敗した処理も対象）。 一時障害のみ最大2回試行。

実行ロール枠：system

参照：a.id、a.quote-b

生成：a.receipt

操作：参照：a.quote-b、DB作成：a.receipt

<a id="p.approve"></a>
## p.approve：承認判断の反映

入力：a.id、a.decision

出力：a.status

応答：あり

<a id="s.approve-lock"></a>
### s.approve-lock：申請単位の排他

排他キー：a.id。範囲：パイプライン終了まで（異常終了を含む）。競合時：拒否。名前空間：business。最大待機：0秒。

実行ロール枠：system

参照：a.id

生成：なし

操作：なし

<a id="s.check-approval"></a>
### s.check-approval：承認対象確認

承認待ちかつ申請者と承認者が別人であることを確認する。

実行ロール枠：system

参照：a.id

生成：なし

操作：なし

<a id="s.approve"></a>
### s.approve：承認

承認済みに更新する。 条件：承認判断がTrueの場合。その他はスキップし次へ合流。

実行ロール枠：system

参照：a.id

生成：a.status

操作：DB更新：a.status

<a id="s.reject"></a>
### s.reject：却下

却下済みに更新する。発注は行わない。 条件：承認判断がFalseの場合。その他はスキップし次へ合流。

実行ロール枠：system

参照：a.id

生成：a.status

操作：DB更新：a.status

<a id="p.dispatch"></a>
## p.dispatch：発注確定の起動

入力：a.id

出力：a.id

応答：あり

<a id="s.dispatch"></a>
### s.dispatch：引継ぎ条件確認

承認済みの購買申請IDを次ワークフローへ引き継ぐ。

実行ロール枠：system

参照：a.id

生成：なし

操作：なし

<a id="p.confirm"></a>
## p.confirm：発注確定

入力：a.id

出力：なし

応答：なし

<a id="s.order-lock"></a>
### s.order-lock：申請単位の排他

排他キー：a.id。範囲：パイプライン終了まで（異常終了を含む）。競合時：拒否。名前空間：business。最大待機：0秒。

実行ロール枠：system

参照：a.id

生成：なし

操作：なし

<a id="s.eligibility"></a>
### s.eligibility：発注条件照会

承認済み、見積書2件あり、未発注であることを確認する。

実行ロール枠：system

参照：a.id

生成：a.eligible

操作：保持：a.eligible

<a id="s.confirm"></a>
### s.confirm：発注確定

発注作成と申請の発注確定済みへの更新を同一DBトランザクションで行う。 条件：発注可能がTrueの場合。その他はスキップし次へ合流。

実行ロール枠：system

参照：a.id

生成：a.order

操作：DB作成：a.order、DB更新：a.status

<a id="s.stop"></a>
### s.stop：発注拒否

発注条件を満たさなければエラーとして終了し、発注しない。 条件：発注可能がFalseの場合。その他はスキップし次へ合流。

実行ロール枠：system

参照：a.id

生成：なし

操作：なし
