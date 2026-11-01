"""Business contracts. Declarations describe behavior; they do not execute it."""
from collections.abc import Mapping
from dataclasses import dataclass, fields
from types import MappingProxyType
from myworkflow.value_objects import ValueObject


class Record(Mapping):
    """Read-only mapping aliases preserve the initial dictionary-facing API."""
    aliases = {}

    def __getitem__(self, key):
        attr = self.aliases.get(key, key)
        if attr.startswith('_') or not hasattr(self, attr):
            raise KeyError(key)
        value = getattr(self, attr)
        if key == 'uses':
            return tuple((u.artifact_id, u.operation) for u in value)
        return value

    def __iter__(self):
        return iter(f.name for f in fields(self))

    def __len__(self):
        return len(fields(self))


@dataclass(frozen=True)
class Role(Record):
    id: str
    name: str  # formal business name
    display_name: str


@dataclass(frozen=True)
class Artifact(Record):
    id: str
    name: str
    key: str = ""
    type: str = "str"
    value_object: ValueObject | None = None


@dataclass(frozen=True)
class Use:
    artifact_id: str
    operation: str  # 参照、保持、DB読取、DB作成、DB更新、送信


@dataclass(frozen=True)
class Step(Record):
    id: str
    name: str
    summary: str
    uses: tuple[Use, ...] = ()
    actor: str = "system"  # abstract role slot, resolved by Binding
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()
    when: tuple[str, bool] | None = None
    attempts: int = 1
    compensate: str | None = None
    kind: str = "action"


@dataclass(frozen=True)
class Lock(Record):
    id: str
    name: str
    keys: tuple[str, ...]  # artifact IDs already in context
    conflict: str = "拒否"
    scope: str = "パイプライン終了まで（異常終了を含む）"
    actor: str = "system"
    namespace: str = "business"
    timeout: float = 0

    @property
    def kind(self): return "lock"

    @property
    def reads(self): return self.keys

    @property
    def writes(self): return ()

    @property
    def uses(self): return ()


@dataclass(frozen=True)
class Pipeline(Record):
    id: str
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]  # produced artifact IDs, not fields of PipelineResult
    steps: tuple[Step | Lock, ...]
    reply: bool = True


@dataclass(frozen=True)
class Trigger(Record):
    aliases = {"role": "actor_role_id", "mapping": "mapping"}
    id: str
    name: str
    input_mapping: tuple[tuple[str, str], ...]
    after: str | None = None
    wait: str | None = None
    actor_role_id: str | None = None

    @property
    def mapping(self): return MappingProxyType(dict(self.input_mapping))


@dataclass(frozen=True)
class Binding(Record):
    aliases = {"pipeline": "pipeline_id", "next_workflow": "next_workflow_id"}
    id: str  # placement identity, independent of reusable pipeline identity
    pipeline_id: str
    trigger: str
    input_mapping: tuple[tuple[str, str], ...]  # contract input -> source description
    after: str | None = None  # preceding placement, if any
    wait: str | None = None
    next_workflow_id: str | None = None
    additional_triggers: tuple[Trigger, ...] = ()
    actor_role_id: str | None = None
    role_mapping: tuple[tuple[str, str], ...] = ()  # abstract slot -> concrete role ID
    trigger_id: str | None = None

    @property
    def triggers(self):
        return (Trigger(self.trigger_id or self.id, self.trigger, self.input_mapping, self.after, self.wait, self.actor_role_id), *self.additional_triggers)


@dataclass(frozen=True)
class Workflow(Record):
    id: str
    name: str
    bindings: tuple[Binding, ...]


@dataclass(frozen=True)
class ContractCatalog:
    """業務契約カタログ: shared business declarations and value definitions."""
    artifacts: tuple[Artifact, ...]
    pipelines: tuple[Pipeline, ...]
    workflows: tuple[Workflow, ...]
    roles: tuple[Role, ...] = ()
    value_objects: tuple[ValueObject, ...] = ()

    def validate(self) -> None:
        from myworkflow.validation import validate_catalog
        validate_catalog(self)


# Backward-compatible import; new code uses the explicit business contract name.
Catalog = ContractCatalog
