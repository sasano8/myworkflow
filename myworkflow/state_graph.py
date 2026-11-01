"""State graph declarations; optional execution is provided by TransitionRuntime."""
from dataclasses import dataclass
from collections.abc import Callable
from inspect import isfunction

from myworkflow.errors import ContractError
from myworkflow.markdown import escape
from myworkflow.models import Binding, Catalog, Trigger, Workflow


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

    def validate(self, catalog: Catalog) -> None:
        catalog.validate()
        if not any(w is self.workflow for w in catalog.workflows):
            raise ContractError(f'{self.workflow.id}: workflow must belong to catalog')
        if not isinstance(self.states, tuple) or not isinstance(self.transitions, tuple):
            raise ContractError(f'{self.workflow.id}: graph declarations must be tuples')
        ids = {e.id for e in (*catalog.artifacts, *catalog.roles, *catalog.pipelines, *catalog.workflows, *catalog.value_objects)}
        ids.update(s.id for p in catalog.pipelines for s in p.steps)
        ids.update(b.id for w in catalog.workflows for b in w.bindings)
        ids.update(t.id for w in catalog.workflows for b in w.bindings for t in b.triggers)
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
            if transition.trigger not in transition.binding.triggers:
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

    def to_dict(self, catalog: Catalog) -> dict:
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


def render_state_graph(graph: StateGraph, catalog: Catalog) -> str:
    """Render declarations, not a runtime state/history report."""
    graph.validate(catalog)
    roles = {r.id: r.display_name for r in catalog.roles}
    pipelines = {p.id: p.name for p in catalog.pipelines}
    lines = ['# 状態遷移', '',
             '| 連番 | ワークフロー | トランジション | 実行者 | トリガー | 現在の状態 | 成功後の状態 | 条件 | パイプライン | 固定ID |',
             '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for number, t in enumerate(graph.transitions, 1):
        cells = (f'{number:03}', graph.workflow.name, t.name, roles[t.trigger.actor_role_id],
                 t.trigger.name, t.source.name, t.target.name, t.condition or '—',
                 pipelines[t.binding.pipeline_id], f'{graph.workflow.id}/{t.id}')
        lines.append('| ' + ' | '.join(escape(c) for c in cells) + ' |')
    return '\n'.join(lines) + '\n'
