# メールで届いた申請書の受付（人手）

固定ID：w.manual_receipt

[ワークフロー一覧](../workflows.md)

人だけで行う業務の記述用サンプルです。申請者がメールを送り、受付担当者がメールソフトで受信・確認し、受付台帳へ記入します。メール受信・添付取得・台帳更新を自動実行するものではありません。実行ハンドラー・Engine・配備用のBuildConfigは定義しません。

## 処理・配置

### b.manual_receipt

処理：[p.manual_receipt](../shared-definitions.md#p.manual_receipt)

ステップ：[s.mail_receive](../shared-definitions.md#s.mail_receive) → [s.mail_record](../shared-definitions.md#s.mail_record)

ロール割当：system → [role.mail_clerk](../shared-definitions.md#role.mail_clerk)、clerk → [role.mail_clerk](../shared-definitions.md#role.mail_clerk)

- t.application_mail：申請者から申請書添付メールが届く／実行者：[role.mail_requester](../shared-definitions.md#role.mail_requester)
  入力元：[a.application_mail](../shared-definitions.md#a.application_mail) ← 共有メールボックスで受信した申請メール


## ロール

- [role.mail_requester](../shared-definitions.md#role.mail_requester)：申請者
- [role.mail_clerk](../shared-definitions.md#role.mail_clerk)：受付担当者

## 状態・遷移

初期状態：state.mail_received

- state.mail_received：申請メール受信
- state.mail_registered：受付台帳記入済み

| 遷移 | 現在 | 成功後 | 配置・トリガー | 条件 |
| --- | --- | --- | --- | --- |
| tr.mail_register | state.mail_received | state.mail_registered | b.manual_receipt/t.application_mail | 添付申請書を確認し、受付台帳への記入を終えた／ガード：なし |

## 接続・待機

未定義。

## データ

- [a.application_mail](../shared-definitions.md#a.application_mail)：申請メール
- [a.application_form](../shared-definitions.md#a.application_form)：添付申請書
- [a.receipt_entry](../shared-definitions.md#a.receipt_entry)：受付台帳の記入内容

## 受入条件

未定義。

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
