# 業務要件と受入条件の対応

[業務要件](requirements.md)

## 受入条件との対応

<a id="b.approve"></a>
### b.approve

- [申請者のロールでは承認できない](acceptance.md#scenario.purchase.authorization)

<a id="c.delete-a"></a>
### c.delete-a

- [見積書登録と補償：2件とも成功](acceptance.md#scenario.purchase.upload.success)
- [見積書登録と補償：1件目の保存失敗](acceptance.md#scenario.purchase.upload.first-failure)
- [見積書登録と補償：一時障害から回復](acceptance.md#scenario.purchase.upload.transient)
- [見積書登録と補償：応答消失から回復](acceptance.md#scenario.purchase.upload.lost-response)
- [見積書登録と補償：2件目の最終失敗による打ち消し](acceptance.md#scenario.purchase.upload.final-failure)
- [見積書登録と補償：応答消失後も今回の登録物を回収](acceptance.md#scenario.purchase.upload.lost-final)
- [補償に失敗しても保存基盤を開き直して復旧できる](acceptance.md#scenario.purchase.recovery)
- [補償時に別の実行が所有するファイルを削除しない](acceptance.md#scenario.purchase.ownership)

<a id="c.delete-b"></a>
### c.delete-b

- [見積書登録と補償：2件とも成功](acceptance.md#scenario.purchase.upload.success)
- [見積書登録と補償：1件目の保存失敗](acceptance.md#scenario.purchase.upload.first-failure)
- [見積書登録と補償：一時障害から回復](acceptance.md#scenario.purchase.upload.transient)
- [見積書登録と補償：応答消失から回復](acceptance.md#scenario.purchase.upload.lost-response)
- [見積書登録と補償：2件目の最終失敗による打ち消し](acceptance.md#scenario.purchase.upload.final-failure)
- [見積書登録と補償：応答消失後も今回の登録物を回収](acceptance.md#scenario.purchase.upload.lost-final)

<a id="p.approve"></a>
### p.approve

- [却下した購買申請は予定日時を過ぎても発注しない](acceptance.md#scenario.purchase.reject)
- [Temporalでも却下した申請を発注しない](acceptance.md#scenario.purchase.temporal-reject)

<a id="p.confirm"></a>
### p.confirm

- [承認済みの購買申請を指定日時に一度だけ発注する](acceptance.md#scenario.purchase.schedule)
- [却下した購買申請は予定日時を過ぎても発注しない](acceptance.md#scenario.purchase.reject)
- [承認済みでも見積書がなければ発注できない](acceptance.md#scenario.purchase.missing-quotes)

<a id="p.upload"></a>
### p.upload

- [見積書登録と補償：2件とも成功](acceptance.md#scenario.purchase.upload.success)
- [見積書登録と補償：1件目の保存失敗](acceptance.md#scenario.purchase.upload.first-failure)
- [見積書登録と補償：一時障害から回復](acceptance.md#scenario.purchase.upload.transient)
- [見積書登録と補償：応答消失から回復](acceptance.md#scenario.purchase.upload.lost-response)
- [見積書登録と補償：2件目の最終失敗による打ち消し](acceptance.md#scenario.purchase.upload.final-failure)
- [見積書登録と補償：応答消失後も今回の登録物を回収](acceptance.md#scenario.purchase.upload.lost-final)
- [補償に失敗しても保存基盤を開き直して復旧できる](acceptance.md#scenario.purchase.recovery)
- [補償時に別の実行が所有するファイルを削除しない](acceptance.md#scenario.purchase.ownership)

<a id="w.approval"></a>
### w.approval

- [承認済みの購買申請を指定日時に一度だけ発注する](acceptance.md#scenario.purchase.schedule)
- [承認待ちを経て発注が一度だけ確定する](acceptance.md#scenario.purchase.temporal-approve)
- [Temporalでも却下した申請を発注しない](acceptance.md#scenario.purchase.temporal-reject)

<a id="w.execution"></a>
### w.execution

- [承認待ちを経て発注が一度だけ確定する](acceptance.md#scenario.purchase.temporal-approve)
