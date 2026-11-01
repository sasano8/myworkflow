"""Versioned field changes; only the transition runner may prepare and commit them."""
from copy import deepcopy
from dataclasses import dataclass

from myworkflow.artifact_jobs import ArtifactWrite
from myworkflow.errors import ContractError


@dataclass(frozen=True)
class Record:
    key: str
    version: int
    _value: dict

    @property
    def value(self) -> dict:
        return deepcopy(self._value)


class Changes:
    """Read handles preserve original versions; update() never publishes a write."""
    def __init__(self, coordinator):
        self._coordinator = coordinator
        self._records: dict[str, Record] = {}
        self._updates: dict[str, dict] = {}
        self._closed = False
        self._subject: Record | None = None

    @property
    def subject(self) -> Record:
        if self._subject is None:
            raise ContractError('No transition subject is bound')
        return self._subject

    def read(self, key: str) -> Record:
        if self._closed:
            raise ContractError('Changes are closed')
        if key not in self._records:
            snapshot = self._coordinator.read(key)
            if snapshot is None:
                raise ContractError(f'{key}: record does not exist')
            if not isinstance(snapshot.value, dict):
                raise ContractError(f'{key}: field updates require a JSON object')
            self._records[key] = Record(key, snapshot.version, deepcopy(snapshot.value))
        return self._records[key]

    def update(self, record: Record, **fields) -> None:
        if self._closed:
            raise ContractError('Changes are closed')
        if not isinstance(record, Record) or self._records.get(record.key) is not record:
            raise ContractError('update requires a record read by this Changes instance')
        value = self._updates.setdefault(record.key, record.value)
        value.update(deepcopy(fields))

    def _writes(self) -> tuple[ArtifactWrite, ...]:
        return tuple(ArtifactWrite(key, deepcopy(value), self._records[key].version)
                     for key, value in sorted(self._updates.items()))

    def _close(self):
        self._closed = True
