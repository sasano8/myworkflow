"""Execution-independent contract for prepared artifacts and their final commit."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


type ArtifactValue = None | bool | int | float | str | list[ArtifactValue] | dict[str, ArtifactValue]


class JobState(StrEnum):
    PREPARED = 'prepared'
    COMMITTED = 'committed'
    DISCARDED = 'discarded'


@dataclass(frozen=True)
class ArtifactWrite:
    key: str
    value: ArtifactValue
    expected_version: int = 0  # zero requires the artifact to be absent


@dataclass(frozen=True)
class ArtifactSnapshot:
    key: str
    value: ArtifactValue
    version: int


@dataclass(frozen=True)
class ArtifactJob:
    job_id: str
    state: JobState
    keys: tuple[str, ...]
    versions: tuple[tuple[str, int], ...] = ()  # versions committed by this job, not today's values


class JobConflict(ValueError):
    """The job ID has already been bound to a different request."""


class ArtifactConflict(ValueError):
    """A committed version changed after this request was prepared."""


class InvalidJobState(ValueError):
    """A discarded job cannot commit; a committed job cannot discard."""


@runtime_checkable
class ArtifactCoordinator(Protocol):
    """Providers own storage/atomicity; pipelines stage changes and ask for a commit.

    Implementations must bind a job ID to exactly one immutable request, keep
    outcomes queryable, and commit writes and the receipt atomically within their
    advertised storage boundary. Network/transaction details are not pipeline code.
    """
    def read(self, key: str) -> ArtifactSnapshot | None: ...
    def prepare(self, job_id: str, writes: tuple[ArtifactWrite, ...]) -> ArtifactJob: ...
    def commit(self, job_id: str) -> ArtifactJob: ...
    def status(self, job_id: str) -> ArtifactJob | None: ...
    def discard(self, job_id: str) -> ArtifactJob: ...
