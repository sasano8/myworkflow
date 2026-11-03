# トランジション契約に従う申請承認

固定ID：w.guarded_approval

[ワークフロー一覧](../workflows.md)

## 処理・配置

### b.guarded_approve

処理：[p.guarded_approve](../shared-definitions.md#p.guarded_approve)

ステップ：[s.guarded_approve](../shared-definitions.md#s.guarded_approve)

ロール割当：system → [role.guarded_system](../shared-definitions.md#role.guarded_system)

- t.guarded_approve：承認操作／実行者：[role.guarded_reviewer](../shared-definitions.md#role.guarded_reviewer)
  入力元：[a.guarded_id](../shared-definitions.md#a.guarded_id) ← id


## ロール

- [role.guarded_system](../shared-definitions.md#role.guarded_system)：システム
- [role.guarded_reviewer](../shared-definitions.md#role.guarded_reviewer)：承認者

## 状態・遷移

初期状態：state.guarded_waiting

- state.guarded_waiting：承認待ち
- state.guarded_approved：承認済み

| 遷移 | 現在 | 成功後 | 配置・トリガー | 条件 |
| --- | --- | --- | --- | --- |
| tr.guarded_approve | state.guarded_waiting | state.guarded_approved | b.guarded_approve/t.guarded_approve | 申請者本人ではなく、金額が正である／ガード：examples.feature_demos.approval_values.application.may_approve |

## 接続・待機

未定義。

## データ

- [a.guarded_id](../shared-definitions.md#a.guarded_id)：申請ID

## 受入条件

未定義。

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
