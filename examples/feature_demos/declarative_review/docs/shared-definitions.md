# 共有定義

[ワークフロー一覧](workflows.md)

<a id="role.system"></a>
## role.system：業務システム

システム

<a id="role.requester"></a>
## role.requester：申請部門の担当者

申請者

<a id="role.approver"></a>
## role.approver：申請内容を審査する責任者

承認者

<a id="a.review_id"></a>
## a.review_id：申請ID

キー：application_id／型：str

<a id="a.review_decision"></a>
## a.review_decision：審査判断

キー：decision／型：str

<a id="p.review_submit"></a>
## p.review_submit：申請内容の受付

入力：a.review_id

出力：a.review_id

応答：あり

<a id="s.review_submit"></a>
### s.review_submit：申請の記録

申請内容を受け付ける。

実行ロール枠：system

参照：a.review_id

生成：なし

操作：参照：a.review_id

<a id="p.review_record"></a>
## p.review_record：審査結果の反映

入力：a.review_id、a.review_decision

出力：a.review_id

応答：あり

<a id="s.review_record"></a>
### s.review_record：審査操作の記録

対象申請に対する審査判断（承認・差戻し・却下）を記録する。

実行ロール枠：system

参照：a.review_id、a.review_decision

生成：なし

操作：参照：a.review_id、参照：a.review_decision
