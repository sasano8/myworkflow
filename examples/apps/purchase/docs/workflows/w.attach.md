# 購買申請への見積書添付

固定ID：w.attach

[ワークフロー一覧](../workflows.md)

## 処理・配置

### b.upload

処理：[p.upload](../shared-definitions.md#p.upload)

ステップ：[s.upload-lock](../shared-definitions.md#s.upload-lock) → [s.check-upload](../shared-definitions.md#s.check-upload) → [s.put-a](../shared-definitions.md#s.put-a) → [s.put-b](../shared-definitions.md#s.put-b)

ロール割当：system → [role.system](../shared-definitions.md#role.system)

- t.upload：申請者が見積書2件をアップロード／実行者：[role.requester](../shared-definitions.md#role.requester)
  入力元：[a.id](../shared-definitions.md#a.id) ← id、[a.quote-a](../shared-definitions.md#a.quote-a) ← file_a、[a.quote-b](../shared-definitions.md#a.quote-b) ← file_b


## ロール

- [role.requester](../shared-definitions.md#role.requester)：申請者
- [role.system](../shared-definitions.md#role.system)：システム

## 状態・遷移

未定義。

## 接続・待機

未定義。

## データ

- [a.id](../shared-definitions.md#a.id)：購買申請ID
- [a.quote-a](../shared-definitions.md#a.quote-a)：見積書A
- [a.quote-b](../shared-definitions.md#a.quote-b)：見積書B
- [a.receipt](../shared-definitions.md#a.receipt)：添付登録結果

## 受入条件

- [見積書登録と補償：2件とも成功](../acceptance.md#scenario.purchase.upload.success)：p.upload、c.delete-a、c.delete-b
- [見積書登録と補償：1件目の保存失敗](../acceptance.md#scenario.purchase.upload.first-failure)：p.upload、c.delete-a、c.delete-b
- [見積書登録と補償：一時障害から回復](../acceptance.md#scenario.purchase.upload.transient)：p.upload、c.delete-a、c.delete-b
- [見積書登録と補償：応答消失から回復](../acceptance.md#scenario.purchase.upload.lost-response)：p.upload、c.delete-a、c.delete-b
- [見積書登録と補償：2件目の最終失敗による打ち消し](../acceptance.md#scenario.purchase.upload.final-failure)：p.upload、c.delete-a、c.delete-b
- [見積書登録と補償：応答消失後も今回の登録物を回収](../acceptance.md#scenario.purchase.upload.lost-final)：p.upload、c.delete-a、c.delete-b
- [補償に失敗しても保存基盤を開き直して復旧できる](../acceptance.md#scenario.purchase.recovery)：p.upload、c.delete-a
- [補償時に別の実行が所有するファイルを削除しない](../acceptance.md#scenario.purchase.ownership)：p.upload、c.delete-a

宣言から生成した仕様です。受入テストの成功や実行時の状態を示すものではありません。
