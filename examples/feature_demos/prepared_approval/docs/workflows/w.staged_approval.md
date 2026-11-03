# 申請の準備と承認確定

固定ID：w.staged_approval

[ワークフロー一覧](../workflows.md)

## 処理・配置

### b.staged_approve

処理：[p.staged_approval](../shared-definitions.md#p.staged_approval)

ステップ：[s.staged_read](../shared-definitions.md#s.staged_read) → [s.staged_prepare](../shared-definitions.md#s.staged_prepare) → [s.staged_commit](../shared-definitions.md#s.staged_commit)

ロール割当：system → [role.staged_system](../shared-definitions.md#role.staged_system)

- t.staged_approve：承認操作／実行者：[role.staged_reviewer](../shared-definitions.md#role.staged_reviewer)
  入力元：[a.staged_id](../shared-definitions.md#a.staged_id) ← id


## ロール

- [role.staged_system](../shared-definitions.md#role.staged_system)：システム
- [role.staged_reviewer](../shared-definitions.md#role.staged_reviewer)：承認者

## 状態・遷移

初期状態：state.staged_pending

- state.staged_pending：承認待ち
- state.staged_approved：承認済み

| 遷移 | 現在 | 成功後 | 配置・トリガー | 条件 |
| --- | --- | --- | --- | --- |
| tr.staged_approve | state.staged_pending | state.staged_approved | b.staged_approve/t.staged_approve | 未定義／ガード：なし |

## 接続・待機

未定義。

## データ

- [a.staged_id](../shared-definitions.md#a.staged_id)：申請ID
- [a.staged_version](../shared-definitions.md#a.staged_version)：申請バージョン
- [a.staged_state_version](../shared-definitions.md#a.staged_state_version)：状態バージョン
- [a.staged_changes](../shared-definitions.md#a.staged_changes)：確定予定の申請内容

## 受入条件

未定義。

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
