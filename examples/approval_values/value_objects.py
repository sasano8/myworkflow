"""Data contracts shared by documentation, input validation and final commit."""
from datetime import date
from typing import Annotated

from pydantic import ConfigDict, Field, RootModel, model_validator

from myworkflow import ValueModel, ValueObject

Yen = Annotated[int, Field(strict=True, gt=0, description='税込の購買申請金額。単位は円。', examples=[10000])]


class PurchaseAmount(RootModel[Yen]):
    """円単位の正の整数。通貨換算や税額計算はしない。"""
    model_config = ConfigDict(frozen=True, strict=True, validate_default=True)


class ApplicationId(RootModel[Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{1,64}$',
                                                 description='申請を識別する英数字・ハイフン・アンダースコア。',
                                                 examples=['purchase_001'])]]):
    model_config = ConfigDict(frozen=True, strict=True, validate_default=True)


class ApprovalApplication(ValueModel):
    owner: str = Field(min_length=1, description='申請者の利用者ID。', examples=['alice'])
    amount: Yen
    status: str = Field(min_length=1, description='状態宣言の固定ID。開始・終了状態はトランジションで照合する。')
    approved_by: str | None = Field(default=None, min_length=1, description='承認者の利用者ID。未承認ならnull。')


class DeliveryPeriod(ValueModel):
    starts_on: date = Field(description='納品受付開始日。', examples=['2026-11-01'])
    ends_on: date = Field(description='納品受付終了日。開始日を含め、終了日は開始日以降。', examples=['2026-11-30'])

    @model_validator(mode='after')
    def dates_in_order(self):
        if self.ends_on < self.starts_on:
            raise ValueError('終了日は開始日以降である必要があります')
        return self


purchase_amount = ValueObject('vo.purchase_amount', '購買申請金額', PurchaseAmount,
                              '税込・円単位の金額。0円と負の金額、小数や文字列は受け付けない。')
application_identifier = ValueObject('vo.application_id', '購買申請ID', ApplicationId)
approval_application = ValueObject('vo.approval_application', '承認対象の購買申請', ApprovalApplication,
                                   '同一レコードに業務項目と状態を保存する。操作可否はトランジションで検証する。')
delivery_period = ValueObject('vo.delivery_period', '納品受付期間', DeliveryPeriod,
                              rules=('終了日は開始日以降とする。同日も許可する。',))
