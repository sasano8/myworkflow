# 共有定義

[ワークフロー一覧](workflows.md)

人だけで行う業務の記述用サンプルです。申請者がメールを送り、受付担当者がメールソフトで受信・確認し、受付台帳へ記入します。メール受信・添付取得・台帳更新を自動実行するものではありません。実行ハンドラー・Engine・配備用のBuildConfigは定義しません。

<a id="role.mail_requester"></a>
## role.mail_requester：申請書をメールで送付する部門の担当者

申請者

<a id="role.mail_clerk"></a>
## role.mail_clerk：申請メールと添付書類を確認し台帳へ記入する担当者

受付担当者

<a id="a.application_mail"></a>
## a.application_mail：申請メール

キー：mail／型：str

<a id="a.application_form"></a>
## a.application_form：添付申請書

キー：form／型：str

<a id="a.receipt_entry"></a>
## a.receipt_entry：受付台帳の記入内容

キー：entry／型：str

<a id="p.manual_receipt"></a>
## p.manual_receipt：メールによる申請書受付（人手）

入力：a.application_mail

出力：a.receipt_entry

応答：なし

<a id="s.mail_receive"></a>
### s.mail_receive：申請書をメールで受信する

受付担当者が共有メールボックスを開き、送信者と添付申請書を確認する。添付がなければ申請者へ再送を依頼する。

実行ロール枠：clerk

参照：a.application_mail

生成：a.application_form

操作：参照：a.application_mail、保持：a.application_form

<a id="s.mail_record"></a>
### s.mail_record：受付台帳へ記入する

受付担当者が申請書を読み、申請者・件名・受信日時を受付台帳へ手作業で記入する。

実行ロール枠：clerk

参照：a.application_mail、a.application_form

生成：a.receipt_entry

操作：参照：a.application_form、保持：a.receipt_entry
