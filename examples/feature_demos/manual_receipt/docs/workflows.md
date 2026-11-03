# ワークフロー一覧

人だけで行う業務の記述用サンプルです。申請者がメールを送り、受付担当者がメールソフトで受信・確認し、受付台帳へ記入します。メール受信・添付取得・台帳更新を自動実行するものではありません。実行ハンドラー・Engine・配備用のBuildConfigは定義しません。

[共有定義](shared-definitions.md)

| 固定ID | ワークフロー | 呼び出すロール | 配置数 |
| --- | --- | --- | --- |
| w.manual_receipt | [メールで届いた申請書の受付（人手）](workflows/w.manual_receipt.md) | [申請者](shared-definitions.md#role.mail_requester) | 1 |

## 未配置の共有定義

なし。

## ワークフローに未対応の受入条件

なし。
