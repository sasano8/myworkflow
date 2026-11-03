# ワークフロー一覧

[共有定義](shared-definitions.md)

| 固定ID | ワークフロー | 呼び出すロール | 配置数 |
| --- | --- | --- | --- |
| w.approval | [購買申請の受付・承認](workflows/w.approval.md) | [申請者](shared-definitions.md#role.requester)、[承認者](shared-definitions.md#role.approver)、[発注担当者](shared-definitions.md#role.buyer)、[システム](shared-definitions.md#role.system) | 3 |
| w.attach | [購買申請への見積書添付](workflows/w.attach.md) | [申請者](shared-definitions.md#role.requester) | 1 |
| w.execution | [承認済み購買申請の発注確定](workflows/w.execution.md) | [システム](shared-definitions.md#role.system) | 1 |

## 未配置の共有定義

なし。

## ワークフローに未対応の受入条件

なし。
