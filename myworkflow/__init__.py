"""Public declarations; implementations live in focused modules."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from myworkflow.syntax import (
        step,
        pipeline,
        workflow,
        role,
        artifact,
        mutex,
        trigger,
        binding,
        state,
        transition,
        operation,
    )

from myworkflow.contracts.annotations import Annotated, annotate, declaration
from myworkflow.contracts.handlers import HandlerContract
from myworkflow.contracts.catalogs import RootCatalog
from myworkflow.contracts.models import (
    Artifact,
    Binding,
    Catalog,
    ContractCatalog,
    Lock,
    Pipeline,
    Role,
    Step,
    Trigger,
    Use,
    Workflow,
)
from myworkflow.contracts.value_objects import ValueModel, ValueObject
from myworkflow.contracts.results import Message, MessageLevel, PipelineResult
from myworkflow.contracts.errors import BusinessError, PipelineError

__all__ = [
    "role",
    "artifact",
    "mutex",
    "trigger",
    "binding",
    "state",
    "transition",
    "operation",
    "step",
    "pipeline",
    "workflow",
    "HandlerContract",
    "Annotated",
    "annotate",
    "declaration",
    "ValueModel",
    "ValueObject",
    "Message",
    "MessageLevel",
    "PipelineResult",
    "PipelineError",
    "BusinessError",
    "Artifact",
    "Binding",
    "ContractCatalog",
    "RootCatalog",
    "Catalog",
    "Lock",
    "Pipeline",
    "Role",
    "Step",
    "Trigger",
    "Use",
    "Workflow",
    "render",
]


def render(catalog: ContractCatalog) -> str:
    """Public convenience entrypoint; rendering is implemented in generation."""
    from myworkflow.generation.documents import render as render_catalog

    return render_catalog(catalog)


def __getattr__(name):
    if name in (
        "step",
        "pipeline",
        "workflow",
        "role",
        "artifact",
        "mutex",
        "trigger",
        "binding",
        "state",
        "transition",
        "operation",
    ):
        from importlib import import_module

        value = getattr(import_module("myworkflow.syntax"), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
