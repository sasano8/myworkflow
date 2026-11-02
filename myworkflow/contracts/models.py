"""Business contracts. Declarations describe behavior; they do not execute it."""
from myworkflow.contracts.annotations import Extensible
from dataclasses import dataclass
from myworkflow.contracts.value_objects import ValueObject


@dataclass(frozen=True)
class Role(Extensible):
    id: str
    name: str  # formal business name
    display_name: str


@dataclass(frozen=True)
class Artifact(Extensible):
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
class Step(Extensible):
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
class Lock(Extensible):
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
class Pipeline(Extensible):
    id: str
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]  # produced artifact IDs, not fields of PipelineResult
    steps: tuple[Step | Lock, ...]
    reply: bool = True


@dataclass(frozen=True)
class Trigger(Extensible):
    id: str
    name: str
    input_mapping: tuple[tuple[str, str], ...]
    after: str | None = None
    wait: str | None = None
    actor_role_id: str | None = None


@dataclass(frozen=True)
class Binding(Extensible):
    id: str
    pipeline_id: str
    triggers: tuple[Trigger, ...]
    role_mapping: tuple[tuple[str, str], ...] = ()
    next_workflow_id: str | None = None


@dataclass(frozen=True)
class Workflow(Extensible):
    id: str
    name: str
    bindings: tuple[Binding, ...]


@dataclass(frozen=True)
class ContractCatalog(Extensible):
    """業務契約カタログ: shared business declarations and value definitions."""
    artifacts: tuple[Artifact, ...]
    pipelines: tuple[Pipeline, ...]
    workflows: tuple[Workflow, ...]
    roles: tuple[Role, ...] = ()
    value_objects: tuple[ValueObject, ...] = ()

    @property
    def entities(self):
        return (*self.artifacts, *self.pipelines, *self.workflows, *self.roles, *self.value_objects,
                *(s for p in self.pipelines for s in p.steps),
                *(b for w in self.workflows for b in w.bindings),
                *(t for w in self.workflows for b in w.bindings for t in b.triggers))

    def validate(self) -> None:
        from myworkflow.contracts.validation import validate_catalog
        validate_catalog(self)


# Backward-compatible import; new code uses the explicit business contract name.
Catalog = ContractCatalog
