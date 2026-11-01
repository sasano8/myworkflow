"""Generated interfaces. Edit the contract, then regenerate."""
from dataclasses import dataclass
from myworkflow.results import PipelineResult as _PipelineResult

@dataclass(frozen=True)
class PSubmitRequest:
    application_id: str
    vendor: str
    amount: int

PSubmitResponse = _PipelineResult

@dataclass(frozen=True)
class PUploadRequest:
    application_id: str
    quote_a: str
    quote_b: str

PUploadResponse = _PipelineResult

@dataclass(frozen=True)
class PApproveRequest:
    application_id: str
    decision: bool

PApproveResponse = _PipelineResult

@dataclass(frozen=True)
class PDispatchRequest:
    application_id: str

PDispatchResponse = _PipelineResult

@dataclass(frozen=True)
class PConfirmRequest:
    application_id: str

PConfirmResponse = _PipelineResult
