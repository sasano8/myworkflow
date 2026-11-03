"""Dedicated syntax that only builds declarations and attaches the shared protocol."""
from collections.abc import Callable, Mapping
from typing import TypeVar

from myworkflow.contracts.annotations import annotate
from myworkflow.contracts.models import Artifact
from myworkflow.compiler.pipelines import Operation, PipelineDeclaration, StepDeclaration
from myworkflow.compiler.declarations import WorkflowDeclaration

F = TypeVar('F', bound=Callable)


def step(*, id: str, name: str = '', summary: str = '',
         reads: tuple[Artifact, ...] = (), writes: tuple[Artifact, ...] = (),
         uses: tuple[tuple[Artifact, str], ...] = (), when: tuple[Artifact, bool] | None = None,
         compensate: Operation | Callable | None = None, attempts: int = 1, actor: str = 'system',
         extensions: Mapping[str, object] | None = None) -> Callable[[F], F]:
    return annotate(StepDeclaration(id, name, summary, reads, writes, uses, when, compensate, attempts, actor,
                                    extensions={} if extensions is None else extensions))


def pipeline(*, id: str, name: str = '', inputs: tuple[Artifact, ...] = (),
             produces: tuple[Artifact, ...] = (), steps: tuple[object, ...] = (), reply: bool = True,
             extensions: Mapping[str, object] | None = None) -> Callable[[F], F]:
    def decorate(target: F) -> F:
        return annotate(PipelineDeclaration(id, name or target.__name__, inputs, produces, steps, reply,
                                             extensions={} if extensions is None else extensions))(target)
    return decorate


def workflow(*, id: str, name: str = '', members: tuple[object, ...] = (),
             extensions: Mapping[str, object] | None = None) -> Callable[[F], F]:
    def decorate(target: F) -> F:
        return annotate(WorkflowDeclaration(id, name or target.__name__, members,
                                             extensions={} if extensions is None else extensions))(target)
    return decorate
