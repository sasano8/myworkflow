"""Screen specifications referencing existing workflow entry points; no UI runtime."""
from dataclasses import dataclass
import re

from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.models import ContractCatalog


@dataclass(frozen=True)
class WorkflowCall:
    workflow_id: str
    binding_id: str
    trigger_id: str


@dataclass(frozen=True)
class ScreenFeature:
    id: str
    name: str
    event: str
    description: str
    workflow_call: WorkflowCall | None = None


@dataclass(frozen=True)
class Screen:
    id: str
    name: str
    features: tuple[ScreenFeature, ...]


def validate_screens(screens: tuple[Screen, ...], catalog: ContractCatalog) -> None:
    catalog.validate()
    if not isinstance(screens, tuple) or any(not isinstance(s, Screen) for s in screens):
        raise ContractError('screens: expected a tuple of Screen')
    workflows = {w.id: w for w in catalog.workflows}
    ids = set()

    def identity(entity):
        if (not isinstance(entity.id, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', entity.id)
                or entity.id in ids):
            raise ContractError('screens: IDs must be unique and contain no slash')
        ids.add(entity.id)
        if not isinstance(entity.name, str) or not entity.name.strip():
            raise ContractError(f'{entity.id}: name is required')

    for screen in screens:
        identity(screen)
        if not isinstance(screen.features, tuple) or any(not isinstance(f, ScreenFeature) for f in screen.features):
            raise ContractError(f'{screen.id}: expected a tuple of ScreenFeature')
        for feature in screen.features:
            identity(feature)
            for field in ('event', 'description'):
                value = getattr(feature, field)
                if not isinstance(value, str) or not value.strip():
                    raise ContractError(f'{feature.id}: {field} is required')
            call = feature.workflow_call
            if call is None:
                continue
            if not isinstance(call, WorkflowCall):
                raise ContractError(f'{feature.id}: expected WorkflowCall')
            workflow = workflows.get(call.workflow_id)
            if workflow is None:
                raise ContractError(f'{feature.id}: unknown workflow {call.workflow_id}')
            binding = next((b for b in workflow.bindings if b.id == call.binding_id), None)
            if binding is None:
                raise ContractError(f'{feature.id}: binding does not belong to workflow: {call.binding_id}')
            if not any(t.id == call.trigger_id for t in binding.triggers):
                raise ContractError(f'{feature.id}: trigger does not belong to binding: {call.trigger_id}')
