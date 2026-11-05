"""Dedicated syntax that only builds declarations and attaches the shared protocol."""

from collections.abc import Callable, Mapping
from typing import TypeVar

from myworkflow.contracts.annotations import annotate
from myworkflow.contracts.models import Artifact, Role
from myworkflow.compiler.pipelines import (
    Mutex,
    Operation,
    PipelineDeclaration,
    StepDeclaration,
)
from myworkflow.compiler.declarations import (
    Placement,
    StateDeclaration,
    TransitionDeclaration,
    TriggerDeclaration,
    WorkflowDeclaration,
)

F = TypeVar("F", bound=Callable)


def step(
    *,
    id: str,
    name: str = "",
    summary: str = "",
    reads: tuple[Artifact, ...] = (),
    writes: tuple[Artifact, ...] = (),
    uses: tuple[tuple[Artifact, str], ...] = (),
    when: tuple[Artifact, bool] | None = None,
    compensate: Operation | Callable | None = None,
    attempts: int = 1,
    actor: str = "system",
    extensions: Mapping[str, object] | None = None,
) -> Callable[[F], F]:
    return annotate(
        StepDeclaration(
            id,
            name,
            summary,
            reads,
            writes,
            uses,
            when,
            compensate,
            attempts,
            actor,
            extensions={} if extensions is None else extensions,
        )
    )


def pipeline(
    *,
    id: str,
    name: str = "",
    inputs: tuple[Artifact, ...] = (),
    produces: tuple[Artifact, ...] = (),
    steps: tuple[object, ...] = (),
    reply: bool = True,
    extensions: Mapping[str, object] | None = None,
) -> Callable[[F], F]:
    def decorate(target: F) -> F:
        return annotate(
            PipelineDeclaration(
                id,
                name or target.__name__,
                inputs,
                produces,
                steps,
                reply,
                extensions={} if extensions is None else extensions,
            )
        )(target)

    return decorate


def workflow(
    *,
    id: str,
    name: str = "",
    members: tuple[object, ...] = (),
    extensions: Mapping[str, object] | None = None,
) -> Callable[[F], F]:
    def decorate(target: F) -> F:
        return annotate(
            WorkflowDeclaration(
                id,
                name or target.__name__,
                members,
                extensions={} if extensions is None else extensions,
            )
        )(target)

    return decorate


def role(
    *,
    id: str,
    name: str,
    display_name: str,
    extensions: Mapping[str, object] | None = None,
) -> Callable[[F], F]:
    return annotate(
        Role(
            id, name, display_name, extensions={} if extensions is None else extensions
        )
    )


def artifact(
    *,
    id: str,
    name: str,
    key: str = "",
    type: str = "str",
    value_object=None,
    extensions: Mapping[str, object] | None = None,
) -> Callable[[F], F]:
    return annotate(
        Artifact(
            id,
            name,
            key,
            type,
            value_object,
            extensions={} if extensions is None else extensions,
        )
    )


def mutex(
    *,
    id: str,
    name: str,
    keys: tuple[object, ...],
    namespace: str = "business",
    timeout: float = 0,
    extensions: Mapping[str, object] | None = None,
) -> Callable[[F], F]:
    return annotate(
        Mutex(
            id,
            name,
            keys,
            namespace,
            timeout,
            extensions={} if extensions is None else extensions,
        )
    )


def trigger(
    *,
    id: str,
    name: str,
    actor: object,
    mapping: tuple[tuple[object, str], ...] = (),
    after: object | None = None,
    wait: str | None = None,
    extensions: Mapping[str, object] | None = None,
) -> Callable[[F], F]:
    return annotate(
        TriggerDeclaration(
            id,
            name,
            actor,
            mapping,
            after,
            wait,
            extensions={} if extensions is None else extensions,
        )
    )


def binding(
    *,
    id: str,
    pipeline: object,
    triggers: tuple[object, ...],
    roles: tuple[tuple[str, object], ...],
    next_workflow: Callable | None = None,
    extensions: Mapping[str, object] | None = None,
) -> Callable[[F], F]:
    return annotate(
        Placement(
            id,
            pipeline,
            triggers,
            roles,
            next_workflow,
            extensions={} if extensions is None else extensions,
        )
    )


def state(
    *,
    id: str,
    name: str,
    initial: bool = False,
    extensions: Mapping[str, object] | None = None,
) -> Callable[[F], F]:
    return annotate(
        StateDeclaration(
            id, name, initial, extensions={} if extensions is None else extensions
        )
    )


def transition(
    *,
    id: str,
    name: str,
    source: object,
    target: object,
    binding: object,
    trigger: object,
    condition: str = "",
    guard: Callable | None = None,
    extensions: Mapping[str, object] | None = None,
) -> Callable[[F], F]:
    return annotate(
        TransitionDeclaration(
            id,
            name,
            source,
            target,
            binding,
            trigger,
            condition,
            guard,
            extensions={} if extensions is None else extensions,
        )
    )


def operation(*, id: str) -> Callable[[F], F]:
    return annotate(Operation(id))
