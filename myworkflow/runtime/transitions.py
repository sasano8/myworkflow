"""Opt-in transition enforcement within one ArtifactCoordinator's commit boundary."""
from copy import deepcopy
from dataclasses import dataclass
from collections.abc import Callable

from myworkflow.errors import ContractError
from myworkflow.runtime.changes import Changes


@dataclass(frozen=True)
class GuardContext:
    """Detached start-of-operation data. A guard must be a pure boolean predicate."""
    actor: str
    application: dict
    inputs: dict


class TransitionRuntime:
    """Bind one declared graph to a JSON record whose field stores a State ID.

    Callers authenticate Principal before invoke. This adapter enforces the role,
    source, guard, unique selection, target and optimistic commit for that record.
    It does not orchestrate waits, authenticate users, or commit external services.
    """
    def __init__(self, compiled, graph, coordinator, *, key: Callable[[dict], str], state_field='status', value_object=None):
        if not any(graph is candidate for candidate in compiled.graphs):
            raise ContractError('Transition graph must belong to compiled declarations')
        graph.validate(compiled.catalog)
        if not callable(key) or not isinstance(state_field, str) or not state_field:
            raise ContractError('Transition runtime requires a key resolver and state field')
        for transition in graph.transitions:
            if transition.condition and transition.guard is None:
                raise ContractError(f'{transition.id}: documented condition requires an executable guard')
        if value_object is not None and not any(value_object is d for d in compiled.catalog.value_objects):
            raise ContractError('Transition record type must reference a declared ValueObject')
        self.value_object = value_object
        self.catalog = compiled.catalog
        self.graph = graph
        self.coordinator = coordinator
        self.key = key
        self.state_field = state_field

    def governs_pipeline(self, pipeline_id):
        return any(b.pipeline_id == pipeline_id for b in self.graph.workflow.bindings)

    def begin(self, ctx, binding_id, trigger_id):
        if binding_id not in {b.id for b in self.graph.workflow.bindings}:
            return None
        key = self.key(dict(ctx.values))
        if not isinstance(key, str) or not key:
            raise ContractError('Transition subject key must be nonempty text')
        changes = Changes(self.coordinator, value_objects=self.catalog.value_objects)
        changes._subject = changes.read(key, value_object=self.value_object)
        original = changes.subject.value
        candidates = []
        for transition in self.graph.transitions:
            if (transition.binding.id != binding_id or transition.trigger.id != trigger_id
                    or original.get(self.state_field) != transition.source.id):
                continue
            if transition.guard is not None:
                accepted = transition.guard(GuardContext(ctx.actor, deepcopy(original), deepcopy(dict(ctx.values))))
                if type(accepted) is not bool:
                    raise ContractError(f'{transition.id}: guard must return bool')
                if not accepted:
                    continue
            candidates.append(transition)
        if len(candidates) != 1:
            raise ContractError(f'{binding_id}/{trigger_id}: expected exactly one eligible transition, got {len(candidates)}')
        ctx.changes = changes
        return TransitionSession(self, candidates[0], changes)


class TransitionSession:
    def __init__(self, runtime, transition, changes):
        self.runtime, self.transition, self.changes = runtime, transition, changes
        # Once prepare is attempted, the durable outcome may require reconciliation.
        self.prepare_attempted = False
        self.committed = False

    def finish(self, ctx):
        writes = self.changes._writes()
        subject = next((w for w in writes if w.key == self.changes.subject.key), None)
        if subject is None or subject.value.get(self.runtime.state_field) != self.transition.target.id:
            raise ContractError(f'{self.transition.id}: changes must set the declared target state {self.transition.target.id}')
        self.changes._close()
        self.prepare_attempted = True
        self.runtime.coordinator.prepare(ctx.run_id, writes)
        ctx.events.append((self.transition.id, 'prepared'))
        self.runtime.coordinator.commit(ctx.run_id)
        self.committed = True
        ctx.events.append((self.transition.id, 'committed'))

    def close(self):
        self.changes._close()
