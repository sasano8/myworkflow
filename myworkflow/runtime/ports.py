"""Runtime infrastructure contracts, independent of any application or database."""

from contextlib import AbstractContextManager
from enum import StrEnum
from typing import Protocol


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    MANUAL_RECOVERY = "manual-recovery"
    COMPENSATED = "compensated"


class LockProvider(Protocol):
    def acquire(
        self, key, *, namespace: str = "business", timeout: float = 0
    ) -> AbstractContextManager: ...


class ExecutionStore(Protocol):
    def begin(self, run_id: str) -> None: ...
    def record(self, run_id: str, events: list, status: str) -> None: ...
