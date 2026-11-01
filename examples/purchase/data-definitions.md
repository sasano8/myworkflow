# データ定義

Pythonのバリューオブジェクトから生成。業務要件の概要とは別に、値の意味と制約を示す。

<a id="vo.purchase.application_id"></a>
## 購買申請ID

固定ID：vo.purchase.application_id。Python型：examples.purchase.value_objects:ApplicationId。

サンプルでは文字列であることを検証する。書式・長さ・空文字の制約は未定義。

| 項目 | 必須 | 説明 | 定義・制約・例 |
| --- | --- | --- | --- |
| (値全体) | 必須 | 購買申請を識別する文字列。 | {"examples": ["purchase-001"], "type": "string"} |

### 補足ルール

補足未記載。

### 完全なJSON Schema

```json
{
  "description": "購買申請を識別する文字列。",
  "examples": [
    "purchase-001"
  ],
  "title": "ApplicationId",
  "type": "string"
}
```

<a id="vo.purchase.vendor"></a>
## 取引先名

固定ID：vo.purchase.vendor。Python型：examples.purchase.value_objects:VendorName。

既存の購買申請処理が要求する取引先名。

| 項目 | 必須 | 説明 | 定義・制約・例 |
| --- | --- | --- | --- |
| (値全体) | 必須 | 購買先の取引先名。 | {"examples": ["サンプル商事"], "minLength": 1, "type": "string"} |

### 補足ルール

- 空文字・空白だけの取引先名を拒否する。前後の空白は削除せず保持する。

独自検証：not_blank。検証の意味は補足ルールと受入テストで確認する。JSON Schemaだけでは全条件を表せない。

### 完全なJSON Schema

```json
{
  "description": "購買先の取引先名。",
  "examples": [
    "サンプル商事"
  ],
  "minLength": 1,
  "title": "VendorName",
  "type": "string"
}
```

<a id="vo.purchase.amount"></a>
## 購買申請金額

固定ID：vo.purchase.amount。Python型：examples.purchase.value_objects:PurchaseAmount。

既存の購買申請処理と同じく0以下を拒否する。通貨単位・税込／税抜の区別は未定義。

| 項目 | 必須 | 説明 | 定義・制約・例 |
| --- | --- | --- | --- |
| (値全体) | 必須 | 正の整数で指定する購買申請金額。 | {"examples": [10000], "exclusiveMinimum": 0, "type": "integer"} |

### 補足ルール

補足未記載。

### 完全なJSON Schema

```json
{
  "description": "正の整数で指定する購買申請金額。",
  "examples": [
    10000
  ],
  "exclusiveMinimum": 0,
  "title": "PurchaseAmount",
  "type": "integer"
}
```

## アーティファクトとの対応

| 固定ID | 名前 | バリューオブジェクト |
| --- | --- | --- |
| a.id | 購買申請ID | vo.purchase.application_id |
| a.vendor | 取引先 | vo.purchase.vendor |
| a.amount | 申請金額 | vo.purchase.amount |

入力と宣言された更新の確定時に検証する。内部の全変数でこのクラスを使うことや、直接DB更新の検証は保証しない。
