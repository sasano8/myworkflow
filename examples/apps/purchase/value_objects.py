"""Purchase value contracts reflecting the sample's existing validation rules."""
from typing import Annotated

from pydantic import ConfigDict, Field, RootModel, field_validator

from myworkflow import ValueObject


class ApplicationId(RootModel[Annotated[str, Field(description='購買申請を識別する文字列。', examples=['purchase-001'])]]):
    model_config = ConfigDict(frozen=True, strict=True, validate_default=True)


class VendorName(RootModel[Annotated[str, Field(min_length=1, description='購買先の取引先名。', examples=['サンプル商事'])]]):
    model_config = ConfigDict(frozen=True, strict=True, validate_default=True)

    @field_validator('root')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('取引先は空白だけにできません')
        return value


class PurchaseAmount(RootModel[Annotated[int, Field(gt=0, description='正の整数で指定する購買申請金額。', examples=[10000])]]):
    model_config = ConfigDict(frozen=True, strict=True, validate_default=True)


application_id_type = ValueObject(
    'vo.purchase.application_id', '購買申請ID', ApplicationId,
    'サンプルでは文字列であることを検証する。書式・長さ・空文字の制約は未定義。',
)
vendor_type = ValueObject(
    'vo.purchase.vendor', '取引先名', VendorName,
    '既存の購買申請処理が要求する取引先名。',
    rules=('空文字・空白だけの取引先名を拒否する。前後の空白は削除せず保持する。',),
)
amount_type = ValueObject(
    'vo.purchase.amount', '購買申請金額', PurchaseAmount,
    '既存の購買申請処理と同じく0以下を拒否する。通貨単位・税込／税抜の区別は未定義。',
)
