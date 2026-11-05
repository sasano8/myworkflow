"""Blob contents live in a file store; only references belong in business metadata."""

from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
import re
from typing import BinaryIO, Protocol, runtime_checkable


@dataclass(frozen=True)
class BlobRef:
    job_id: str
    name: str
    sha256: str
    size: int

    def __post_init__(self):
        if (
            not isinstance(self.job_id, str)
            or not self.job_id.strip()
            or not isinstance(self.name, str)
            or not self.name.strip()
        ):
            raise ValueError("Blob references require a job ID and name")
        if (
            not isinstance(self.sha256, str)
            or re.fullmatch("[0-9a-f]{64}", self.sha256) is None
        ):
            raise ValueError("Blob references require a SHA256 digest")
        if type(self.size) is not int or self.size < 0:
            raise ValueError("Blob size must be a nonnegative integer")


@runtime_checkable
class BlobStore(Protocol):
    def stage_file(self, job_id: str, name: str, source: str | Path) -> BlobRef: ...
    def stage_stream(self, job_id: str, name: str, source: BinaryIO) -> BlobRef: ...
    def list_files(self, job_id: str) -> tuple[BlobRef, ...]: ...
    def open(self, reference: BlobRef) -> AbstractContextManager[BinaryIO]: ...
    def verify(self, reference: BlobRef) -> None: ...
