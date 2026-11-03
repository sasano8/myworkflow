"""Public declarations; implementations live in focused modules."""
from myworkflow.contracts.annotations import Annotated, annotate, declaration
from myworkflow.contracts.handlers import HandlerContract
from myworkflow.contracts.models import Artifact, Binding, Catalog, ContractCatalog, Lock, Pipeline, Role, Step, Trigger, Use, Workflow
from myworkflow.contracts.value_objects import ValueModel, ValueObject
from myworkflow.contracts.results import Message, MessageLevel, PipelineResult
from myworkflow.contracts.errors import BusinessError, PipelineError

__all__ = ["HandlerContract", "Annotated", "annotate", "declaration", "ValueModel", "ValueObject", "Message", "MessageLevel", "PipelineResult", "PipelineError", "BusinessError", "Artifact", "Binding", "ContractCatalog", "Catalog", "Lock", "Pipeline", "Role", "Step", "Trigger", "Use", "Workflow", "render"]


def render(catalog: ContractCatalog) -> str:
    """Public convenience entrypoint; rendering is implemented in generation."""
    from myworkflow.generation.documents import render as render_catalog
    return render_catalog(catalog)
