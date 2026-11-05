"""Generated interfaces. Edit the contract, then regenerate."""

from dataclasses import dataclass
from myworkflow import PipelineResult as _PipelineResult

import examples.apps.purchase.value_objects as _ValueModule0

_Value0 = _ValueModule0.ApplicationId

import examples.apps.purchase.value_objects as _ValueModule1

_Value1 = _ValueModule1.VendorName

import examples.apps.purchase.value_objects as _ValueModule2

_Value2 = _ValueModule2.PurchaseAmount


@dataclass(frozen=True)
class PSubmitRequest:
    application_id: _Value0
    vendor: _Value1
    amount: _Value2


PSubmitResponse = _PipelineResult


@dataclass(frozen=True)
class PUploadRequest:
    application_id: _Value0
    quote_a: str
    quote_b: str


PUploadResponse = _PipelineResult


@dataclass(frozen=True)
class PApproveRequest:
    application_id: _Value0
    decision: bool


PApproveResponse = _PipelineResult


@dataclass(frozen=True)
class PDispatchRequest:
    application_id: _Value0


PDispatchResponse = _PipelineResult


@dataclass(frozen=True)
class PConfirmRequest:
    application_id: _Value0


PConfirmResponse = _PipelineResult
