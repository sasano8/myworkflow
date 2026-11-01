# データ定義

1項目につき1行で表示する。詳細な型・対応・完全なSchemaは[JSON定義](data-definitions.json)を参照。
独自検証はJSON Schemaだけでは全条件を表せないため、補足ルールと受入テストで確認する。

| 定義ID | 項目名 | 型 | 必須 | 説明 | 制約・補足 | 既定値 | 例 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <a id="vo.application_id"></a>vo.application_id | 購買申請ID | 文字列 | 必須 | 申請を識別する英数字・ハイフン・アンダースコア。 | 形式：^[A-Za-z0-9_-]{1,64}$ | — | purchase_001 |
| <a id="vo.purchase_amount"></a>vo.purchase_amount | 購買申請金額 | 整数 | 必須 | 税込の購買申請金額。単位は円。／税込・円単位の金額。0円と負の金額、小数や文字列は受け付けない。 | 0より大きい | — | 10000 |
| <a id="vo.approval_application"></a>vo.approval_application | 承認対象の購買申請.owner | 文字列 | 必須 | 申請者の利用者ID。／定義全体：同一レコードに業務項目と状態を保存する。操作可否はトランジションで検証する。 | 文字数の下限：1／定義全体：未知の項目を拒否 | — | alice |
| vo.approval_application | 承認対象の購買申請.amount | 整数 | 必須 | 税込の購買申請金額。単位は円。 | 0より大きい | — | 10000 |
| vo.approval_application | 承認対象の購買申請.status | 文字列 | 必須 | 状態宣言の固定ID。開始・終了状態はトランジションで照合する。 | 文字数の下限：1 | — | — |
| vo.approval_application | 承認対象の購買申請.approved_by | 文字列 / null | 任意 | 承認者の利用者ID。未承認ならnull。 | 文字数の下限：1 | null | — |
| <a id="vo.delivery_period"></a>vo.delivery_period | 納品受付期間.starts_on | 日付 | 必須 | 納品受付開始日。 | 定義全体：未知の項目を拒否／終了日は開始日以降とする。同日も許可する。／独自検証あり（詳細はJSON参照） | — | 2026-11-01 |
| vo.delivery_period | 納品受付期間.ends_on | 日付 | 必須 | 納品受付終了日。開始日を含め、終了日は開始日以降。 | — | — | 2026-11-30 |
