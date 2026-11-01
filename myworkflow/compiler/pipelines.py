"""Symbolic pipeline declarations; string IDs are produced only during compilation."""
from dataclasses import dataclass

from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.models import Artifact, Lock, Pipeline, Step, Use


@dataclass(frozen=True)
class Operation:
    id: str


@dataclass(frozen=True)
class Action:
    id: str
    name: str
    summary: str
    reads: tuple[Artifact, ...] = ()
    writes: tuple[Artifact, ...] = ()
    uses: tuple[tuple[Artifact, str], ...] = ()
    when: tuple[Artifact, bool] | None = None
    compensate: Operation | None = None
    attempts: int = 1
    actor: str = 'system'  # external abstract role slot, not a role identity


@dataclass(frozen=True)
class Mutex:
    id: str
    name: str
    keys: tuple[Artifact, ...]
    namespace: str = 'business'
    timeout: float = 0


@dataclass(frozen=True)
class PipelineDeclaration:
    id: str
    name: str
    inputs: tuple[Artifact, ...]
    produces: tuple[Artifact, ...]
    steps: tuple[Action | Mutex, ...]
    reply: bool = True


def compile_pipeline(declaration: PipelineDeclaration, artifacts: tuple[Artifact, ...]) -> Pipeline:
    objects = {id(a) for a in artifacts}
    def refs(values, where):
        if not isinstance(values, tuple) or any(not isinstance(a, Artifact) or id(a) not in objects for a in values):
            raise ContractError(f'{where}: expected declared Artifact objects in a tuple')
        if len({id(a) for a in values}) != len(values):
            raise ContractError(f'{where}: duplicate Artifact reference')
        return tuple(a.id for a in values)
    if not isinstance(declaration.steps, tuple):
        raise ContractError(f'{declaration.id}: steps must be a tuple')
    steps = []
    for step in declaration.steps:
        if isinstance(step, Mutex):
            steps.append(Lock(step.id, step.name, refs(step.keys, step.id), namespace=step.namespace,
                              timeout=step.timeout, conflict='待機' if step.timeout else '拒否'))
        elif isinstance(step, Action):
            reads, writes = refs(step.reads, step.id), refs(step.writes, step.id)
            if not isinstance(step.uses, tuple):
                raise ContractError(f'{step.id}: uses must be a tuple')
            uses = []
            for pair in step.uses:
                if not isinstance(pair, tuple) or len(pair) != 2:
                    raise ContractError(f'{step.id}: uses require Artifact/operation pairs')
                refs((pair[0],), step.id)
                uses.append(Use(pair[0].id, pair[1]))
            condition = None
            if step.when is not None:
                if not isinstance(step.when, tuple) or len(step.when) != 2 or type(step.when[1]) is not bool:
                    raise ContractError(f'{step.id}: condition requires an Artifact/boolean pair')
                refs((step.when[0],), step.id)
                condition = (step.when[0].id, step.when[1])
            if step.compensate is not None and not isinstance(step.compensate, Operation):
                raise ContractError(f'{step.id}: compensation must reference Operation')
            steps.append(Step(step.id, step.name, step.summary, tuple(uses), step.actor, reads, writes,
                              condition, step.attempts, step.compensate.id if step.compensate else None))
        else:
            raise ContractError(f'{declaration.id}: steps must reference Action or Mutex')
    return Pipeline(declaration.id, declaration.name, refs(declaration.inputs, declaration.id),
                    refs(declaration.produces, declaration.id), tuple(steps), declaration.reply)
