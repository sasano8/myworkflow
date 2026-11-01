# データ定義

Pythonのバリューオブジェクトから生成。業務要件の概要とは別に、値の意味と制約を示す。

<a id="vo.application_id"></a>
## 購買申請ID

固定ID：vo.application_id。Python型：examples.approval_values:ApplicationId。

説明未記載。

| 項目 | 必須 | 説明 | 定義・制約・例 |
| --- | --- | --- | --- |
| (値全体) | 必須 | 申請を識別する英数字・ハイフン・アンダースコア。 | {"examples": ["purchase_001"], "pattern": "^[A-Za-z0-9_-]{1,64}$", "type": "string"} |

### 補足ルール

補足未記載。

### 完全なJSON Schema

```json
{
  "description": "申請を識別する英数字・ハイフン・アンダースコア。",
  "examples": [
    "purchase_001"
  ],
  "pattern": "^[A-Za-z0-9_-]{1,64}$",
  "title": "ApplicationId",
  "type": "string"
}
```

<a id="vo.purchase_amount"></a>
## 購買申請金額

固定ID：vo.purchase_amount。Python型：examples.approval_values:PurchaseAmount。

税込・円単位の金額。0円と負の金額、小数や文字列は受け付けない。

| 項目 | 必須 | 説明 | 定義・制約・例 |
| --- | --- | --- | --- |
| (値全体) | 必須 | 税込の購買申請金額。単位は円。 | {"examples": [10000], "exclusiveMinimum": 0, "type": "integer"} |

### 補足ルール

補足未記載。

### 完全なJSON Schema

```json
{
  "description": "税込の購買申請金額。単位は円。",
  "examples": [
    10000
  ],
  "exclusiveMinimum": 0,
  "title": "PurchaseAmount",
  "type": "integer"
}
```

<a id="vo.approval_application"></a>
## 承認対象の購買申請

固定ID：vo.approval_application。Python型：examples.approval_values:ApprovalApplication。

同一レコードに業務項目と状態を保存する。操作可否はトランジションで検証する。

| 項目 | 必須 | 説明 | 定義・制約・例 |
| --- | --- | --- | --- |
| owner | 必須 | 申請者の利用者ID。 | {"examples": ["alice"], "minLength": 1, "type": "string"} |
| amount | 必須 | 税込の購買申請金額。単位は円。 | {"examples": [10000], "exclusiveMinimum": 0, "type": "integer"} |
| status | 必須 | 状態宣言の固定ID。開始・終了状態はトランジションで照合する。 | {"minLength": 1, "type": "string"} |
| approved_by | 任意 | 承認者の利用者ID。未承認ならnull。 | {"anyOf": [{"minLength": 1, "type": "string"}, {"type": "null"}], "default": null} |

### 補足ルール

補足未記載。

### 完全なJSON Schema

```json
{
  "additionalProperties": false,
  "properties": {
    "amount": {
      "description": "税込の購買申請金額。単位は円。",
      "examples": [
        10000
      ],
      "exclusiveMinimum": 0,
      "title": "Amount",
      "type": "integer"
    },
    "approved_by": {
      "anyOf": [
        {
          "minLength": 1,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "承認者の利用者ID。未承認ならnull。",
      "title": "Approved By"
    },
    "owner": {
      "description": "申請者の利用者ID。",
      "examples": [
        "alice"
      ],
      "minLength": 1,
      "title": "Owner",
      "type": "string"
    },
    "status": {
      "description": "状態宣言の固定ID。開始・終了状態はトランジションで照合する。",
      "minLength": 1,
      "title": "Status",
      "type": "string"
    }
  },
  "required": [
    "owner",
    "amount",
    "status"
  ],
  "title": "ApprovalApplication",
  "type": "object"
}
```

<a id="vo.delivery_period"></a>
## 納品受付期間

固定ID：vo.delivery_period。Python型：examples.approval_values:DeliveryPeriod。

説明未記載。

| 項目 | 必須 | 説明 | 定義・制約・例 |
| --- | --- | --- | --- |
| starts_on | 必須 | 納品受付開始日。 | {"examples": ["2026-11-01"], "format": "date", "type": "string"} |
| ends_on | 必須 | 納品受付終了日。開始日を含め、終了日は開始日以降。 | {"examples": ["2026-11-30"], "format": "date", "type": "string"} |

### 補足ルール

- 終了日は開始日以降とする。同日も許可する。

独自検証：dates_in_order。検証の意味は補足ルールと受入テストで確認する。JSON Schemaだけでは全条件を表せない。

### 完全なJSON Schema

```json
{
  "additionalProperties": false,
  "properties": {
    "ends_on": {
      "description": "納品受付終了日。開始日を含め、終了日は開始日以降。",
      "examples": [
        "2026-11-30"
      ],
      "format": "date",
      "title": "Ends On",
      "type": "string"
    },
    "starts_on": {
      "description": "納品受付開始日。",
      "examples": [
        "2026-11-01"
      ],
      "format": "date",
      "title": "Starts On",
      "type": "string"
    }
  },
  "required": [
    "starts_on",
    "ends_on"
  ],
  "title": "DeliveryPeriod",
  "type": "object"
}
```

## アーティファクトとの対応

| 固定ID | 名前 | バリューオブジェクト |
| --- | --- | --- |
| a.guarded_id | 申請ID | vo.application_id |

入力と宣言された更新の確定時に検証する。内部の全変数でこのクラスを使うことや、直接DB更新の検証は保証しない。
