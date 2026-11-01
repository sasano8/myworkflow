# データ定義

| 項目 | 内容 |
| --- | --- |
| 用途 | バリューオブジェクトの意味・制約の概要 |
| 詳細 | [機械可読の定義・完全なJSON Schema](data-definitions.json) |
| 検証 | 入力と、型を結び付けた更新の確定時に検証。内部の全変数でのクラス利用や直接DB更新は保証しない |

<a id="vo.purchase.application_id"></a>
## 購買申請ID

| 項目 | 内容 |
| --- | --- |
| 固定ID | vo.purchase.application_id |
| Python型 | examples.purchase.value_objects:ApplicationId |
| 説明 | サンプルでは文字列であることを検証する。書式・長さ・空文字の制約は未定義。 |
| 全体の制約 | — |
| 補足ルール | 未記載 |
| 独自検証 | なし |

| 項目 | 型 | 必須 | 意味 | 制約 | 既定値 | 例 |
| --- | --- | --- | --- | --- | --- | --- |
| (値全体) | 文字列 | 必須 | 購買申請を識別する文字列。 | — | — | purchase-001 |

<a id="vo.purchase.vendor"></a>
## 取引先名

| 項目 | 内容 |
| --- | --- |
| 固定ID | vo.purchase.vendor |
| Python型 | examples.purchase.value_objects:VendorName |
| 説明 | 既存の購買申請処理が要求する取引先名。 |
| 全体の制約 | 文字数の下限：1 |
| 補足ルール | 空文字・空白だけの取引先名を拒否する。前後の空白は削除せず保持する。 |
| 独自検証 | not_blank。意味は補足ルールと受入テストで確認。JSON Schemaだけでは全条件を表せない。 |

| 項目 | 型 | 必須 | 意味 | 制約 | 既定値 | 例 |
| --- | --- | --- | --- | --- | --- | --- |
| (値全体) | 文字列 | 必須 | 購買先の取引先名。 | 文字数の下限：1 | — | サンプル商事 |

<a id="vo.purchase.amount"></a>
## 購買申請金額

| 項目 | 内容 |
| --- | --- |
| 固定ID | vo.purchase.amount |
| Python型 | examples.purchase.value_objects:PurchaseAmount |
| 説明 | 既存の購買申請処理と同じく0以下を拒否する。通貨単位・税込／税抜の区別は未定義。 |
| 全体の制約 | 0より大きい |
| 補足ルール | 未記載 |
| 独自検証 | なし |

| 項目 | 型 | 必須 | 意味 | 制約 | 既定値 | 例 |
| --- | --- | --- | --- | --- | --- | --- |
| (値全体) | 整数 | 必須 | 正の整数で指定する購買申請金額。 | 0より大きい | — | 10000 |

## アーティファクトとの対応

| 固定ID | 名前 | バリューオブジェクト |
| --- | --- | --- |
| a.id | 購買申請ID | vo.purchase.application_id |
| a.vendor | 取引先 | vo.purchase.vendor |
| a.amount | 申請金額 | vo.purchase.amount |
