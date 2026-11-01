"""State graph declarations; optional execution is provided by TransitionRuntime."""
from dataclasses import dataclass
from collections.abc import Callable
from inspect import isfunction

from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.models import Binding, ContractCatalog, Trigger, Workflow


@dataclass(frozen=True)
class State:
    id: str
    name: str


@dataclass(frozen=True)
class Transition:
    id: str
    name: str
    source: State
    target: State
    binding: Binding
    trigger: Trigger
    condition: str = ""
    guard: Callable | None = None


@dataclass(frozen=True)
class StateGraph:
    """Static workflow view. A target is promised only after successful completion.

    This model alone neither executes guards nor updates persisted business state.
    Failure, compensation and commit policies belong to the execution adapter.
    """
    workflow: Workflow
    initial: State
    states: tuple[State, ...]
    transitions: tuple[Transition, ...]

    def validate(self, catalog: ContractCatalog) -> None:
        catalog.validate()
        if not any(w is self.workflow for w in catalog.workflows):
            raise ContractError(f'{self.workflow.id}: workflow must belong to catalog')
        if not isinstance(self.states, tuple) or not isinstance(self.transitions, tuple):
            raise ContractError(f'{self.workflow.id}: graph declarations must be tuples')
        ids = {e.id for e in catalog.entities}
        for entity in (*self.states, *self.transitions):
            if not isinstance(entity.id, str) or not entity.id or not isinstance(entity.name, str) or not entity.name:
                raise ContractError('state graph: nonempty IDs and names are required')
            if entity.id in ids:
                raise ContractError(f'{entity.id}: duplicate graph ID')
            ids.add(entity.id)
        def declared(state):
            return any(state is candidate for candidate in self.states)
        if not declared(self.initial):
            raise ContractError(f'{self.workflow.id}: initial state is not declared')
        for transition in self.transitions:
            if not declared(transition.source) or not declared(transition.target):
                raise ContractError(f'{transition.id}: undeclared source or target state')
            if not any(transition.binding is b for b in self.workflow.bindings):
                raise ContractError(f'{transition.id}: binding must belong to workflow')
            if not any(transition.trigger is t for t in transition.binding.triggers):
                raise ContractError(f'{transition.id}: trigger must belong to binding')
            if transition.guard is not None and not isfunction(transition.guard):
                raise ContractError(f'{transition.id}: guard must be a Python function')
            if not isinstance(transition.condition, str):
                raise ContractError(f'{transition.id}: condition must be text')
        # Reachability, rather than topological sorting: revision/resubmission cycles are legal.
        reachable = {self.initial.id}
        while True:
            expanded = reachable | {t.target.id for t in self.transitions if t.source.id in reachable}
            if expanded == reachable:
                break
            reachable = expanded
        missing = [s.id for s in self.states if s.id not in reachable]
        if missing:
            raise ContractError(f'{self.workflow.id}: unreachable states: {missing}')

    def to_dict(self, catalog: ContractCatalog) -> dict:
        """Normalized comparison/export form; symbolic references become stable IDs."""
        self.validate(catalog)
        return {
            'schema_version': 1,
            'workflow': self.workflow.id,
            'initial': self.initial.id,
            'states': [{'id': s.id, 'name': s.name} for s in self.states],
            'transitions': [{
                'id': t.id, 'name': t.name, 'source': t.source.id, 'target': t.target.id,
                'binding': t.binding.id, 'pipeline': t.binding.pipeline_id,
                'trigger': t.trigger.id, 'actor': t.trigger.actor_role_id,
                'condition': t.condition,
                **({'guard': f"{t.guard.__module__}:{t.guard.__qualname__}"} if t.guard is not None else {}),
            } for t in self.transitions],
        }
