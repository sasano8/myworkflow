"""Symbolic pipeline declarations; string IDs are produced only during compilation."""
from myworkflow.contracts.annotations import Extensible, declaration
from inspect import getdoc
from dataclasses import dataclass
from collections.abc import Callable

from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.models import Artifact, Lock, Pipeline, Step, Use


@dataclass(frozen=True)
class Operation:
    id: str


@dataclass(frozen=True)
class Action(Extensible):
    id: str
    name: str = ""
    summary: str = ""
    reads: tuple[Artifact, ...] = ()
    writes: tuple[Artifact, ...] = ()
    uses: tuple[tuple[Artifact, str], ...] = ()
    when: tuple[Artifact, bool] | None = None
    compensate: Operation | Callable | None = None
    attempts: int = 1
    actor: str = 'system'  # external abstract role slot, not a role identity


@dataclass(frozen=True)
class Mutex(Extensible):
    id: str
    name: str
    keys: tuple[Artifact, ...]
    namespace: str = 'business'
    timeout: float = 0


@dataclass(frozen=True)
class PipelineDeclaration(Extensible):
    id: str
    name: str
    inputs: tuple[Artifact, ...]
    produces: tuple[Artifact, ...]
    steps: tuple[Action | Mutex | Callable, ...]
    reply: bool = True


def compile_pipeline(pipeline: PipelineDeclaration, artifacts: tuple[Artifact, ...]) -> Pipeline:
    objects = {id(a) for a in artifacts}
    def refs(values, where):
        if isinstance(values, tuple):
            values = tuple(declaration(a) for a in values)
        if not isinstance(values, tuple) or any(not isinstance(a, Artifact) or id(a) not in objects for a in values):
            raise ContractError(f'{where}: expected declared Artifact objects in a tuple')
        if len({id(a) for a in values}) != len(values):
            raise ContractError(f'{where}: duplicate Artifact reference')
        return tuple(a.id for a in values)
    if not isinstance(pipeline.steps, tuple):
        raise ContractError(f'{pipeline.id}: steps must be a tuple')
    steps = []
    for target in pipeline.steps:
        step = declaration(target)
        if isinstance(step, Mutex):
            steps.append(Lock(step.id, step.name, refs(step.keys, step.id), namespace=step.namespace,
                              timeout=step.timeout, extensions=step.extensions, conflict='待機' if step.timeout else '拒否'))
        elif isinstance(step, Action):
            reads, writes = refs(step.reads, step.id), refs(step.writes, step.id)
            if not isinstance(step.uses, tuple):
                raise ContractError(f'{step.id}: uses must be a tuple')
            uses = []
            for pair in step.uses:
                if not isinstance(pair, tuple) or len(pair) != 2:
                    raise ContractError(f'{step.id}: uses require Artifact/operation pairs')
                refs((pair[0],), step.id)
                uses.append(Use(declaration(pair[0]).id, pair[1]))
            condition = None
            if step.when is not None:
                if not isinstance(step.when, tuple) or len(step.when) != 2 or type(step.when[1]) is not bool:
                    raise ContractError(f'{step.id}: condition requires an Artifact/boolean pair')
                refs((step.when[0],), step.id)
                condition = (declaration(step.when[0]).id, step.when[1])
            compensation = declaration(step.compensate)
            if compensation is not None and not isinstance(compensation, Operation):
                raise ContractError(f'{step.id}: compensation must reference Operation')
            steps.append(Step(step.id, step.name or getattr(target, '__name__', ''), step.summary or (getdoc(target) if callable(target) else '') or '', tuple(uses), step.actor, reads, writes,
                              condition, step.attempts, compensation.id if compensation else None, extensions=step.extensions))
        else:
            raise ContractError(f'{pipeline.id}: steps must reference Action or Mutex')
    return Pipeline(pipeline.id, pipeline.name, refs(pipeline.inputs, pipeline.id),
                    refs(pipeline.produces, pipeline.id), tuple(steps), pipeline.reply, extensions=pipeline.extensions)
