# チケット発行の受入シナリオ

featureファイルが正本です。この文書は仕様であり、テスト成功の証明ではありません。

<a id="scenario.tickets.issue"></a>
## 受付担当がチケットを発行する

固定ID：`scenario.tickets.issue`。基盤：ローカルEngine。

対象：[ticket.issue](business.md#ticket.issue)

正本：[ tickets.feature:5 ](../acceptance/features/tickets.feature#L5)

| 区分 | 実行者・操作主体 | 条件・操作・期待結果 |
| --- | --- | --- |
| 前提 | 受付担当 | 受付担当が窓口を開いている |
| 操作 | 受付担当 | 受付番号 "T-001" を発行する |
| 期待結果 | 検証基盤 | チケットが1件保存され発行結果が返る |

<details>
<summary>操作・検証の実装対応</summary>

- 受付担当が窓口を開いている → `examples.apps.tickets.acceptance.steps.open_counter`
- 受付番号 "T-001" を発行する → `examples.apps.tickets.acceptance.steps.issue`
- チケットが1件保存され発行結果が返る → `examples.apps.tickets.acceptance.steps.check_ticket`

</details>
