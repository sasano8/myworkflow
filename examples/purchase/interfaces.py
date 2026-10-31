"""Generated interfaces. Edit the contract, then regenerate."""
from dataclasses import dataclass

@dataclass(frozen=True)
class PSubmitRequest:
    application_id: str
    vendor: str
    amount: int

@dataclass(frozen=True)
class PSubmitResponse:
    application_id: str
    status: str

@dataclass(frozen=True)
class PUploadRequest:
    application_id: str
    quote_a: str
    quote_b: str

@dataclass(frozen=True)
class PUploadResponse:
    receipt: str

@dataclass(frozen=True)
class PApproveRequest:
    application_id: str
    decision: bool

@dataclass(frozen=True)
class PApproveResponse:
    status: str

@dataclass(frozen=True)
class PDispatchRequest:
    application_id: str

@dataclass(frozen=True)
class PDispatchResponse:
    application_id: str

@dataclass(frozen=True)
class PConfirmRequest:
    application_id: str

@dataclass(frozen=True)
class PConfirmResponse:
    pass
