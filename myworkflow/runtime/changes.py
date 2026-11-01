"""Versioned field changes; only the transition runner may prepare and commit them."""
from copy import deepcopy
from dataclasses import dataclass

from myworkflow.artifact_jobs import ArtifactWrite
from myworkflow.errors import ContractError
from myworkflow.value_objects import ValueObject


@dataclass(frozen=True)
class Record:
    key: str
    version: int
    _value: dict
    _definition: ValueObject | None = None

    @property
    def value(self) -> dict:
        return deepcopy(self._value)


class Changes:
    """Read handles preserve original versions; update() never publishes a write."""
    def __init__(self, coordinator, *, value_objects=()):
        self._coordinator = coordinator
        self._definitions = value_objects
        self._records: dict[str, Record] = {}
        self._updates: dict[str, dict] = {}
        self._closed = False
        self._subject: Record | None = None

    @property
    def subject(self) -> Record:
        if self._subject is None:
            raise ContractError('No transition subject is bound')
        return self._subject

    def read(self, key: str, *, value_object: ValueObject | None = None) -> Record:
        if self._closed:
            raise ContractError('Changes are closed')
        if value_object is not None and not any(value_object is d for d in self._definitions):
            raise ContractError('Record type must reference a declared ValueObject')
        if key in self._records and value_object is not None and self._records[key]._definition is not value_object:
            raise ContractError(f'{key}: record type cannot be changed after reading')
        if key not in self._records:
            snapshot = self._coordinator.read(key)
            if snapshot is None:
                raise ContractError(f'{key}: record does not exist')
            if not isinstance(snapshot.value, dict):
                raise ContractError(f'{key}: field updates require a JSON object')
            value = value_object.normalize(snapshot.value) if value_object else deepcopy(snapshot.value)
            if not isinstance(value, dict):
                raise ContractError(f'{key}: record contract must produce a JSON object')
            self._records[key] = Record(key, snapshot.version, value, value_object)
        return self._records[key]

    def update(self, record: Record, **fields) -> None:
        if self._closed:
            raise ContractError('Changes are closed')
        if not isinstance(record, Record) or self._records.get(record.key) is not record:
            raise ContractError('update requires a record read by this Changes instance')
        value = self._updates.setdefault(record.key, record.value)
        value.update(deepcopy(fields))

    def _writes(self) -> tuple[ArtifactWrite, ...]:
        writes = []
        for key, value in sorted(self._updates.items()):
            record = self._records[key]
            normalized = record._definition.normalize(value) if record._definition else deepcopy(value)
            if not isinstance(normalized, dict):
                raise ContractError(f'{key}: record contract must produce a JSON object')
            writes.append(ArtifactWrite(key, normalized, record.version))
        return tuple(writes)

    def _close(self):
        self._closed = True
