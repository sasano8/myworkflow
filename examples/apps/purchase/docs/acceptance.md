# 購買フローの受入シナリオ

featureファイルが正本です。この文書は仕様であり、テスト成功の証明ではありません。

<a id="scenario.purchase.schedule"></a>
## 承認済みの購買申請を指定日時に一度だけ発注する

固定ID：`scenario.purchase.schedule`。基盤：ローカルEngine。

対象：[w.approval](business.md#w.approval)、[p.confirm](business.md#p.confirm)

正本：[ purchase.feature:5 ](../acceptance/features/purchase.feature#L5)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | テスト時計 | テスト時計は "2030-04-01T09:00:00+09:00" である |
| 前提 | テスト基盤 | 発注予定日時は "2030-04-01T10:00:00+09:00" である |
| 前提 | 申請者 | 見積書2件を添付した承認待ちの購買申請がある |
| 期待結果 | 検証基盤 | 発注は0件である |
| 操作 | 承認者 | 承認者が承認する |
| 期待結果 | 検証基盤 | 申請状態は "承認済み" である |
| 操作 | テスト時計 | 時計を "2030-04-01T09:59:59+09:00" に進める |
| 期待結果 | 検証基盤 | 発注は0件である |
| 操作 | テスト時計 | 時計を "2030-04-01T01:00:00+00:00" に進める |
| 期待結果 | 検証基盤 | 発注は1件である |
| 期待結果 | 検証基盤 | 申請状態は "発注確定済み" である |
| 操作 | 承認者 | 同じ承認イベントを再送する |
| 期待結果 | 検証基盤 | 発注は1件である |

<details>
<summary>操作・検証の実装対応</summary>

- テスト時計は "2030-04-01T09:00:00+09:00" である → `examples.apps.purchase.acceptance.steps.clock`
- 発注予定日時は "2030-04-01T10:00:00+09:00" である → `examples.apps.purchase.acceptance.steps.schedule`
- 見積書2件を添付した承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.with_quotes`
- 発注は0件である → `examples.apps.purchase.acceptance.steps.order_count`
- 承認者が承認する → `examples.apps.purchase.acceptance.steps.approve`
- 申請状態は "承認済み" である → `examples.apps.purchase.acceptance.steps.application_status`
- 時計を "2030-04-01T09:59:59+09:00" に進める → `examples.apps.purchase.acceptance.steps.advance`
- 発注は0件である → `examples.apps.purchase.acceptance.steps.order_count`
- 時計を "2030-04-01T01:00:00+00:00" に進める → `examples.apps.purchase.acceptance.steps.advance`
- 発注は1件である → `examples.apps.purchase.acceptance.steps.order_count`
- 申請状態は "発注確定済み" である → `examples.apps.purchase.acceptance.steps.application_status`
- 同じ承認イベントを再送する → `examples.apps.purchase.acceptance.steps.duplicate`
- 発注は1件である → `examples.apps.purchase.acceptance.steps.order_count`

</details>

<a id="scenario.purchase.reject"></a>
## 却下した購買申請は予定日時を過ぎても発注しない

固定ID：`scenario.purchase.reject`。基盤：ローカルEngine。

対象：[p.approve](business.md#p.approve)、[p.confirm](business.md#p.confirm)

正本：[ purchase.feature:21 ](../acceptance/features/purchase.feature#L21)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者 | 見積書2件を添付した承認待ちの購買申請がある |
| 操作 | 承認者 | 承認者が却下する |
| 操作 | テスト時計 | 時計を "2030-04-02T10:00:00+09:00" に進める |
| 期待結果 | 検証基盤 | 発注は0件である |
| 期待結果 | 検証基盤 | 申請状態は "却下済み" である |

<details>
<summary>操作・検証の実装対応</summary>

- 見積書2件を添付した承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.with_quotes`
- 承認者が却下する → `examples.apps.purchase.acceptance.steps.reject`
- 時計を "2030-04-02T10:00:00+09:00" に進める → `examples.apps.purchase.acceptance.steps.advance`
- 発注は0件である → `examples.apps.purchase.acceptance.steps.order_count`
- 申請状態は "却下済み" である → `examples.apps.purchase.acceptance.steps.application_status`

</details>

<a id="scenario.purchase.authorization"></a>
## 申請者のロールでは承認できない

固定ID：`scenario.purchase.authorization`。基盤：ローカルEngine。

対象：[b.approve](business.md#b.approve)

正本：[ purchase.feature:29 ](../acceptance/features/purchase.feature#L29)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者 | 見積書2件を添付した承認待ちの購買申請がある |
| 操作 | 申請者 | 申請者が承認を試みる |
| 期待結果 | 検証基盤 | 最後の操作は権限不足である |
| 期待結果 | 検証基盤 | 申請状態は "承認待ち" である |
| 期待結果 | 検証基盤 | 発注は0件である |

<details>
<summary>操作・検証の実装対応</summary>

- 見積書2件を添付した承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.with_quotes`
- 申請者が承認を試みる → `examples.apps.purchase.acceptance.steps.unauthorized`
- 最後の操作は権限不足である → `examples.apps.purchase.acceptance.steps.permission_denied`
- 申請状態は "承認待ち" である → `examples.apps.purchase.acceptance.steps.application_status`
- 発注は0件である → `examples.apps.purchase.acceptance.steps.order_count`

</details>

<a id="scenario.purchase.missing-quotes"></a>
## 承認済みでも見積書がなければ発注できない

固定ID：`scenario.purchase.missing-quotes`。基盤：ローカルEngine。

対象：[p.confirm](business.md#p.confirm)

正本：[ purchase.feature:37 ](../acceptance/features/purchase.feature#L37)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者 | 見積書のない承認待ちの購買申請がある |
| 操作 | 承認者 | 承認者が承認する |
| 操作 | システム | 発注確定を試みる |
| 期待結果 | 検証基盤 | 最後の操作は失敗である |
| 期待結果 | 検証基盤 | 発注は0件である |

<details>
<summary>操作・検証の実装対応</summary>

- 見積書のない承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.without_quotes`
- 承認者が承認する → `examples.apps.purchase.acceptance.steps.approve`
- 発注確定を試みる → `examples.apps.purchase.acceptance.steps.confirm`
- 最後の操作は失敗である → `examples.apps.purchase.acceptance.steps.failed`
- 発注は0件である → `examples.apps.purchase.acceptance.steps.order_count`

</details>

<a id="scenario.purchase.upload.success"></a>
## 見積書登録と補償：2件とも成功

固定ID：`scenario.purchase.upload.success`。基盤：ローカルEngine。

対象：[p.upload](business.md#p.upload)、[c.delete-a](business.md#c.delete-a)、[c.delete-b](business.md#c.delete-b)

正本：[ purchase.feature:56 ](../acceptance/features/purchase.feature#L56)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者 | 見積書のない承認待ちの購買申請がある |
| 前提 | 障害注入基盤 | 保存障害は "障害なし" である |
| 操作 | 申請者 | 申請者が見積書2件を登録する |
| 期待結果 | 検証基盤 | 最後の操作の結果は "成功" である |
| 期待結果 | 検証基盤 | 今回の保存物は2件である |
| 期待結果 | 検証基盤 | 添付登録は2件である |
| 期待結果 | 検証基盤 | 補償呼出しは0件である |

<details>
<summary>操作・検証の実装対応</summary>

- 見積書のない承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.without_quotes`
- 保存障害は "障害なし" である → `examples.apps.purchase.acceptance.steps.failures`
- 申請者が見積書2件を登録する → `examples.apps.purchase.acceptance.steps.upload`
- 最後の操作の結果は "成功" である → `examples.apps.purchase.acceptance.steps.result`
- 今回の保存物は2件である → `examples.apps.purchase.acceptance.steps.objects`
- 添付登録は2件である → `examples.apps.purchase.acceptance.steps.attachments`
- 補償呼出しは0件である → `examples.apps.purchase.acceptance.steps.compensations`

</details>

<a id="scenario.purchase.upload.first-failure"></a>
## 見積書登録と補償：1件目の保存失敗

固定ID：`scenario.purchase.upload.first-failure`。基盤：ローカルEngine。

対象：[p.upload](business.md#p.upload)、[c.delete-a](business.md#c.delete-a)、[c.delete-b](business.md#c.delete-b)

正本：[ purchase.feature:57 ](../acceptance/features/purchase.feature#L57)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者 | 見積書のない承認待ちの購買申請がある |
| 前提 | 障害注入基盤 | 保存障害は "見積書Aが2回とも保存前に失敗" である |
| 操作 | 申請者 | 申請者が見積書2件を登録する |
| 期待結果 | 検証基盤 | 最後の操作の結果は "失敗" である |
| 期待結果 | 検証基盤 | 今回の保存物は0件である |
| 期待結果 | 検証基盤 | 添付登録は0件である |
| 期待結果 | 検証基盤 | 補償呼出しは1件である |

<details>
<summary>操作・検証の実装対応</summary>

- 見積書のない承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.without_quotes`
- 保存障害は "見積書Aが2回とも保存前に失敗" である → `examples.apps.purchase.acceptance.steps.failures`
- 申請者が見積書2件を登録する → `examples.apps.purchase.acceptance.steps.upload`
- 最後の操作の結果は "失敗" である → `examples.apps.purchase.acceptance.steps.result`
- 今回の保存物は0件である → `examples.apps.purchase.acceptance.steps.objects`
- 添付登録は0件である → `examples.apps.purchase.acceptance.steps.attachments`
- 補償呼出しは1件である → `examples.apps.purchase.acceptance.steps.compensations`

</details>

<a id="scenario.purchase.upload.transient"></a>
## 見積書登録と補償：一時障害から回復

固定ID：`scenario.purchase.upload.transient`。基盤：ローカルEngine。

対象：[p.upload](business.md#p.upload)、[c.delete-a](business.md#c.delete-a)、[c.delete-b](business.md#c.delete-b)

正本：[ purchase.feature:58 ](../acceptance/features/purchase.feature#L58)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者 | 見積書のない承認待ちの購買申請がある |
| 前提 | 障害注入基盤 | 保存障害は "見積書Bが1回だけ保存前に失敗" である |
| 操作 | 申請者 | 申請者が見積書2件を登録する |
| 期待結果 | 検証基盤 | 最後の操作の結果は "成功" である |
| 期待結果 | 検証基盤 | 今回の保存物は2件である |
| 期待結果 | 検証基盤 | 添付登録は2件である |
| 期待結果 | 検証基盤 | 補償呼出しは0件である |

<details>
<summary>操作・検証の実装対応</summary>

- 見積書のない承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.without_quotes`
- 保存障害は "見積書Bが1回だけ保存前に失敗" である → `examples.apps.purchase.acceptance.steps.failures`
- 申請者が見積書2件を登録する → `examples.apps.purchase.acceptance.steps.upload`
- 最後の操作の結果は "成功" である → `examples.apps.purchase.acceptance.steps.result`
- 今回の保存物は2件である → `examples.apps.purchase.acceptance.steps.objects`
- 添付登録は2件である → `examples.apps.purchase.acceptance.steps.attachments`
- 補償呼出しは0件である → `examples.apps.purchase.acceptance.steps.compensations`

</details>

<a id="scenario.purchase.upload.lost-response"></a>
## 見積書登録と補償：応答消失から回復

固定ID：`scenario.purchase.upload.lost-response`。基盤：ローカルEngine。

対象：[p.upload](business.md#p.upload)、[c.delete-a](business.md#c.delete-a)、[c.delete-b](business.md#c.delete-b)

正本：[ purchase.feature:59 ](../acceptance/features/purchase.feature#L59)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者 | 見積書のない承認待ちの購買申請がある |
| 前提 | 障害注入基盤 | 保存障害は "見積書Bが1回だけ保存後に応答消失" である |
| 操作 | 申請者 | 申請者が見積書2件を登録する |
| 期待結果 | 検証基盤 | 最後の操作の結果は "成功" である |
| 期待結果 | 検証基盤 | 今回の保存物は2件である |
| 期待結果 | 検証基盤 | 添付登録は2件である |
| 期待結果 | 検証基盤 | 補償呼出しは0件である |

<details>
<summary>操作・検証の実装対応</summary>

- 見積書のない承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.without_quotes`
- 保存障害は "見積書Bが1回だけ保存後に応答消失" である → `examples.apps.purchase.acceptance.steps.failures`
- 申請者が見積書2件を登録する → `examples.apps.purchase.acceptance.steps.upload`
- 最後の操作の結果は "成功" である → `examples.apps.purchase.acceptance.steps.result`
- 今回の保存物は2件である → `examples.apps.purchase.acceptance.steps.objects`
- 添付登録は2件である → `examples.apps.purchase.acceptance.steps.attachments`
- 補償呼出しは0件である → `examples.apps.purchase.acceptance.steps.compensations`

</details>

<a id="scenario.purchase.upload.final-failure"></a>
## 見積書登録と補償：2件目の最終失敗による打ち消し

固定ID：`scenario.purchase.upload.final-failure`。基盤：ローカルEngine。

対象：[p.upload](business.md#p.upload)、[c.delete-a](business.md#c.delete-a)、[c.delete-b](business.md#c.delete-b)

正本：[ purchase.feature:60 ](../acceptance/features/purchase.feature#L60)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者 | 見積書のない承認待ちの購買申請がある |
| 前提 | 障害注入基盤 | 保存障害は "見積書Bが2回とも保存前に失敗" である |
| 操作 | 申請者 | 申請者が見積書2件を登録する |
| 期待結果 | 検証基盤 | 最後の操作の結果は "失敗" である |
| 期待結果 | 検証基盤 | 今回の保存物は0件である |
| 期待結果 | 検証基盤 | 添付登録は0件である |
| 期待結果 | 検証基盤 | 補償呼出しは2件である |

<details>
<summary>操作・検証の実装対応</summary>

- 見積書のない承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.without_quotes`
- 保存障害は "見積書Bが2回とも保存前に失敗" である → `examples.apps.purchase.acceptance.steps.failures`
- 申請者が見積書2件を登録する → `examples.apps.purchase.acceptance.steps.upload`
- 最後の操作の結果は "失敗" である → `examples.apps.purchase.acceptance.steps.result`
- 今回の保存物は0件である → `examples.apps.purchase.acceptance.steps.objects`
- 添付登録は0件である → `examples.apps.purchase.acceptance.steps.attachments`
- 補償呼出しは2件である → `examples.apps.purchase.acceptance.steps.compensations`

</details>

<a id="scenario.purchase.upload.lost-final"></a>
## 見積書登録と補償：応答消失後も今回の登録物を回収

固定ID：`scenario.purchase.upload.lost-final`。基盤：ローカルEngine。

対象：[p.upload](business.md#p.upload)、[c.delete-a](business.md#c.delete-a)、[c.delete-b](business.md#c.delete-b)

正本：[ purchase.feature:61 ](../acceptance/features/purchase.feature#L61)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者 | 見積書のない承認待ちの購買申請がある |
| 前提 | 障害注入基盤 | 保存障害は "見積書Bが2回とも保存後に応答消失" である |
| 操作 | 申請者 | 申請者が見積書2件を登録する |
| 期待結果 | 検証基盤 | 最後の操作の結果は "失敗" である |
| 期待結果 | 検証基盤 | 今回の保存物は0件である |
| 期待結果 | 検証基盤 | 添付登録は0件である |
| 期待結果 | 検証基盤 | 補償呼出しは2件である |

<details>
<summary>操作・検証の実装対応</summary>

- 見積書のない承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.without_quotes`
- 保存障害は "見積書Bが2回とも保存後に応答消失" である → `examples.apps.purchase.acceptance.steps.failures`
- 申請者が見積書2件を登録する → `examples.apps.purchase.acceptance.steps.upload`
- 最後の操作の結果は "失敗" である → `examples.apps.purchase.acceptance.steps.result`
- 今回の保存物は0件である → `examples.apps.purchase.acceptance.steps.objects`
- 添付登録は0件である → `examples.apps.purchase.acceptance.steps.attachments`
- 補償呼出しは2件である → `examples.apps.purchase.acceptance.steps.compensations`

</details>

<a id="scenario.purchase.recovery"></a>
## 補償に失敗しても保存基盤を開き直して復旧できる

固定ID：`scenario.purchase.recovery`。基盤：ローカルEngine。

対象：[p.upload](business.md#p.upload)、[c.delete-a](business.md#c.delete-a)

正本：[ purchase.feature:64 ](../acceptance/features/purchase.feature#L64)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者 | 見積書のない承認待ちの購買申請がある |
| 前提 | 障害注入基盤 | 保存障害は "見積書Bが最終失敗し見積書Aの削除も失敗" である |
| 操作 | 申請者 | 申請者が見積書2件を登録する |
| 期待結果 | 検証基盤 | 最後の操作の結果は "失敗" である |
| 期待結果 | 検証基盤 | 復旧状態は "手動復旧待ち" である |
| 期待結果 | 検証基盤 | 今回の保存物は1件である |
| 操作 | 復旧担当者 | 保存基盤を開き直して手動復旧する |
| 操作 | 復旧担当者 | 保存基盤を開き直して手動復旧する |
| 期待結果 | 検証基盤 | 今回の保存物は0件である |
| 期待結果 | 検証基盤 | 復旧状態は "補償完了" である |

<details>
<summary>操作・検証の実装対応</summary>

- 見積書のない承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.without_quotes`
- 保存障害は "見積書Bが最終失敗し見積書Aの削除も失敗" である → `examples.apps.purchase.acceptance.steps.failures`
- 申請者が見積書2件を登録する → `examples.apps.purchase.acceptance.steps.upload`
- 最後の操作の結果は "失敗" である → `examples.apps.purchase.acceptance.steps.result`
- 復旧状態は "手動復旧待ち" である → `examples.apps.purchase.acceptance.steps.recovery_state`
- 今回の保存物は1件である → `examples.apps.purchase.acceptance.steps.objects`
- 保存基盤を開き直して手動復旧する → `examples.apps.purchase.acceptance.steps.recover`
- 保存基盤を開き直して手動復旧する → `examples.apps.purchase.acceptance.steps.recover`
- 今回の保存物は0件である → `examples.apps.purchase.acceptance.steps.objects`
- 復旧状態は "補償完了" である → `examples.apps.purchase.acceptance.steps.recovery_state`

</details>

<a id="scenario.purchase.ownership"></a>
## 補償時に別の実行が所有するファイルを削除しない

固定ID：`scenario.purchase.ownership`。基盤：ローカルEngine。

対象：[p.upload](business.md#p.upload)、[c.delete-a](business.md#c.delete-a)

正本：[ purchase.feature:77 ](../acceptance/features/purchase.feature#L77)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者 | 見積書のない承認待ちの購買申請がある |
| 前提 | 障害注入基盤 | 保存障害は "見積書Bが最終失敗し見積書Aの削除も失敗" である |
| 操作 | 申請者 | 申請者が見積書2件を登録する |
| 操作 | 障害注入基盤 | 残存ファイルが別の実行のバージョンに置き換わる |
| 操作 | 復旧担当者 | 保存基盤を開き直して手動復旧する |
| 期待結果 | 検証基盤 | 最後の操作の結果は "失敗" である |
| 期待結果 | 検証基盤 | 別の実行のファイルは1件である |
| 期待結果 | 検証基盤 | 復旧状態は "手動復旧待ち" である |

<details>
<summary>操作・検証の実装対応</summary>

- 見積書のない承認待ちの購買申請がある → `examples.apps.purchase.acceptance.steps.without_quotes`
- 保存障害は "見積書Bが最終失敗し見積書Aの削除も失敗" である → `examples.apps.purchase.acceptance.steps.failures`
- 申請者が見積書2件を登録する → `examples.apps.purchase.acceptance.steps.upload`
- 残存ファイルが別の実行のバージョンに置き換わる → `examples.apps.purchase.acceptance.steps.replace_owner`
- 保存基盤を開き直して手動復旧する → `examples.apps.purchase.acceptance.steps.recover`
- 最後の操作の結果は "失敗" である → `examples.apps.purchase.acceptance.steps.result`
- 別の実行のファイルは1件である → `examples.apps.purchase.acceptance.steps.other_objects`
- 復旧状態は "手動復旧待ち" である → `examples.apps.purchase.acceptance.steps.recovery_state`

</details>

<a id="scenario.purchase.temporal-approve"></a>
## 承認待ちを経て発注が一度だけ確定する

固定ID：`scenario.purchase.temporal-approve`。基盤：Temporal。

対象：[w.approval](business.md#w.approval)、[w.execution](business.md#w.execution)

正本：[ temporal.feature:6 ](../acceptance/features/temporal.feature#L6)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者・Temporal | Temporalで購買申請が承認待ちになっている |
| 期待結果 | 検証基盤 | 発注は0件である |
| 操作 | 承認者 | 承認者が承認する |
| 操作 | 承認者 | 同じ承認イベントを再送する |
| 操作 | テスト基盤 | ワークフローの完了を待つ |
| 期待結果 | 検証基盤 | 発注は1件である |
| 期待結果 | 検証基盤 | 申請状態は "発注確定済み" である |

<details>
<summary>操作・検証の実装対応</summary>

- Temporalで購買申請が承認待ちになっている → `examples.apps.purchase.acceptance.steps.temporal_wait`
- 発注は0件である → `examples.apps.purchase.acceptance.steps.order_count`
- 承認者が承認する → `examples.apps.purchase.acceptance.steps.approve`
- 同じ承認イベントを再送する → `examples.apps.purchase.acceptance.steps.duplicate`
- ワークフローの完了を待つ → `examples.apps.purchase.acceptance.steps.wait_completed`
- 発注は1件である → `examples.apps.purchase.acceptance.steps.order_count`
- 申請状態は "発注確定済み" である → `examples.apps.purchase.acceptance.steps.application_status`

</details>

<a id="scenario.purchase.temporal-reject"></a>
## Temporalでも却下した申請を発注しない

固定ID：`scenario.purchase.temporal-reject`。基盤：Temporal。

対象：[w.approval](business.md#w.approval)、[p.approve](business.md#p.approve)

正本：[ temporal.feature:16 ](../acceptance/features/temporal.feature#L16)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 申請者・Temporal | Temporalで購買申請が承認待ちになっている |
| 操作 | 承認者 | 承認者が却下する |
| 操作 | テスト基盤 | ワークフローの完了を待つ |
| 期待結果 | 検証基盤 | 発注は0件である |
| 期待結果 | 検証基盤 | 申請状態は "却下済み" である |

<details>
<summary>操作・検証の実装対応</summary>

- Temporalで購買申請が承認待ちになっている → `examples.apps.purchase.acceptance.steps.temporal_wait`
- 承認者が却下する → `examples.apps.purchase.acceptance.steps.reject`
- ワークフローの完了を待つ → `examples.apps.purchase.acceptance.steps.wait_completed`
- 発注は0件である → `examples.apps.purchase.acceptance.steps.order_count`
- 申請状態は "却下済み" である → `examples.apps.purchase.acceptance.steps.application_status`

</details>
