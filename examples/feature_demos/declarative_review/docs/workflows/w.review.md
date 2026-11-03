# 申請内容の審査と再申請

固定ID：w.review

[ワークフロー一覧](../workflows.md)

## 処理・配置

### b.review_submit

処理：[p.review_submit](../shared-definitions.md#p.review_submit)

ステップ：[s.review_submit](../shared-definitions.md#s.review_submit)

ロール割当：system → [role.system](../shared-definitions.md#role.system)

- t.review_submit：申請操作／実行者：[role.requester](../shared-definitions.md#role.requester)
  入力元：[a.review_id](../shared-definitions.md#a.review_id) ← id

### b.review_record

処理：[p.review_record](../shared-definitions.md#p.review_record)

ステップ：[s.review_record](../shared-definitions.md#s.review_record)

ロール割当：system → [role.system](../shared-definitions.md#role.system)

- t.review_approve：承認操作／実行者：[role.approver](../shared-definitions.md#role.approver)
  入力元：[a.review_id](../shared-definitions.md#a.review_id) ← id、[a.review_decision](../shared-definitions.md#a.review_decision) ← decision

- t.review_return：差戻し操作／実行者：[role.approver](../shared-definitions.md#role.approver)
  入力元：[a.review_id](../shared-definitions.md#a.review_id) ← id、[a.review_decision](../shared-definitions.md#a.review_decision) ← decision

- t.review_reject：却下操作／実行者：[role.approver](../shared-definitions.md#role.approver)
  入力元：[a.review_id](../shared-definitions.md#a.review_id) ← id、[a.review_decision](../shared-definitions.md#a.review_decision) ← decision

### b.review_resubmit

処理：[p.review_submit](../shared-definitions.md#p.review_submit)

ステップ：[s.review_submit](../shared-definitions.md#s.review_submit)

ロール割当：system → [role.system](../shared-definitions.md#role.system)

- t.review_resubmit：再申請操作／実行者：[role.requester](../shared-definitions.md#role.requester)
  入力元：[a.review_id](../shared-definitions.md#a.review_id) ← id


## ロール

- [role.system](../shared-definitions.md#role.system)：システム
- [role.requester](../shared-definitions.md#role.requester)：申請者
- [role.approver](../shared-definitions.md#role.approver)：承認者

## 状態・遷移

初期状態：state.review_draft

- state.review_draft：未申請
- state.review_pending：承認待ち
- state.review_revising：修正待ち
- state.review_approved：承認済み
- state.review_rejected：却下済み

| 遷移 | 現在 | 成功後 | 配置・トリガー | 条件 |
| --- | --- | --- | --- | --- |
| tr.review_submit | state.review_draft | state.review_pending | b.review_submit/t.review_submit | 未定義／ガード：なし |
| tr.review_approve | state.review_pending | state.review_approved | b.review_record/t.review_approve | 判断が承認で、承認権限があり、申請者本人ではない／ガード：なし |
| tr.review_return | state.review_pending | state.review_revising | b.review_record/t.review_return | 判断が差戻し／ガード：なし |
| tr.review_resubmit | state.review_revising | state.review_pending | b.review_resubmit/t.review_resubmit | 未定義／ガード：なし |
| tr.review_reject | state.review_pending | state.review_rejected | b.review_record/t.review_reject | 判断が却下／ガード：なし |

## 接続・待機

未定義。

## データ

- [a.review_id](../shared-definitions.md#a.review_id)：申請ID
- [a.review_decision](../shared-definitions.md#a.review_decision)：審査判断

## 受入条件

未定義。

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
