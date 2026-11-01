"""Experimental named class declarations compiled without running business handlers.

Use objects to connect declarations. Stable IDs only identify exported contracts.
"""
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from myworkflow.errors import ContractError
from myworkflow.models import Artifact, Binding, Catalog, Pipeline, Role, Trigger, Workflow
from myworkflow.program import Program
from myworkflow.state_graph import State, StateGraph, Transition


@dataclass(frozen=True)
class StateDeclaration(State):
    initial: bool = False


@dataclass(frozen=True)
class TriggerDeclaration:
    id: str
    name: str
    actor: Role
    mapping: tuple[tuple[Artifact, str], ...] = ()
    after: 'Placement | None' = None
    wait: str | None = None


@dataclass(frozen=True)
class Placement:
    id: str
    pipeline: Pipeline
    triggers: tuple[TriggerDeclaration, ...]
    roles: tuple[tuple[str, Role], ...]
    next_workflow: type | None = None


@dataclass(frozen=True)
class TransitionDeclaration:
    id: str
    name: str
    source: StateDeclaration
    target: StateDeclaration
    binding: Placement
    trigger: TriggerDeclaration
    condition: str = ''


@dataclass(frozen=True)
class WorkflowOptions:
    id: str
    name: str


@dataclass(frozen=True)
class CompiledWorkflows:
    program: Program
    graphs: tuple[StateGraph, ...]

    @property
    def catalog(self):
        return self.program.model


# Short declaration names, with dataclass signatures available to editors.
state = StateDeclaration
trigger = TriggerDeclaration
bind = Placement
transition = TransitionDeclaration


T = TypeVar('T')


def workflow(*, id: str, name: str) -> Callable[[type[T]], type[T]]:
    """Keep the class and its named attributes available to IDEs and other declarations."""
    def decorate(cls: type[T]) -> type[T]:
        if not isinstance(cls, type):
            raise ContractError('@workflow requires a class')
        if '__workflow_options__' in vars(cls):
            raise ContractError(f'{id}: workflow already decorated')
        if cls.__bases__ != (object,):
            raise ContractError(f'{id}: workflow inheritance is not supported')
        setattr(cls, '__workflow_options__', WorkflowOptions(id, name))
        return cls
    return decorate


def compile_workflows(*declarations: type, artifacts: tuple[Artifact, ...] = ()) -> CompiledWorkflows:
    """Compile all explicitly selected classes in definition order.

    No methods, properties, generators or handlers are invoked to discover nodes.
    Pipelines and roles are collected from placements; artifacts are explicit because
    the existing Pipeline model still stores artifact references as IDs.
    """
    def fail(where, message):
        raise ContractError(f'{where}: {message}')

    def sequence(value, typ, where):
        if not isinstance(value, tuple) or any(not isinstance(v, typ) for v in value):
            fail(where, f'expected a tuple of {typ.__name__}')

    sequence(artifacts, Artifact, 'artifacts')
    if len({id(a) for a in artifacts}) != len(artifacts):
        fail('artifacts', 'duplicate declaration')
    if not declarations:
        fail('workflows', 'at least one class is required')
    if len({id(c) for c in declarations}) != len(declarations):
        fail('workflows', 'duplicate class')
    metadata = {}
    members = {}
    for cls in declarations:
        if not isinstance(cls, type) or not isinstance(vars(cls).get('__workflow_options__'), WorkflowOptions):
            fail('workflow', 'expected a class decorated with @workflow')
        if cls.__bases__ != (object,):
            fail(cls.__name__, 'workflow inheritance is not supported')
        options = vars(cls)['__workflow_options__']
        metadata[cls] = options
        named = [(name, value) for name, value in vars(cls).items()
                 if isinstance(value, (StateDeclaration, Placement, TransitionDeclaration))]
        if len({id(value) for _, value in named}) != len(named):
            fail(options.id, 'declaration aliases are not supported')
        members[cls] = tuple(value for _, value in named)

    pipelines, roles = {}, {}
    artifact_objects = {id(a) for a in artifacts}

    def collect(target, obj, typ, where):
        if not isinstance(obj, typ):
            fail(where, f'expected {typ.__name__} reference')
        if obj.id in target and target[obj.id] is not obj:
            fail(where, f'{obj.id}: different objects share a stable ID')
        target[obj.id] = obj

    workflows, graphs = [], []
    for cls in declarations:
        options = metadata[cls]
        values = members[cls]
        states = tuple(v for v in values if isinstance(v, StateDeclaration))
        placements = tuple(v for v in values if isinstance(v, Placement))
        transitions = tuple(v for v in values if isinstance(v, TransitionDeclaration))
        if any(type(s.initial) is not bool for s in states):
            fail(options.id, 'initial must be boolean')
        initial = [s for s in states if s.initial]
        if len(initial) != 1:
            fail(options.id, 'exactly one initial state is required')
        placement_objects = {id(p) for p in placements}
        bindings = {}
        compiled_triggers = {}
        for p in placements:
            collect(pipelines, p.pipeline, Pipeline, p.id)
            sequence(p.triggers, TriggerDeclaration, p.id + '.triggers')
            if not p.triggers or len({id(t) for t in p.triggers}) != len(p.triggers):
                fail(p.id, 'at least one distinct trigger is required')
            if not isinstance(p.roles, tuple):
                fail(p.id, 'roles must be a tuple of slot/Role pairs')
            role_mapping = []
            for pair in p.roles:
                if not isinstance(pair, tuple) or len(pair) != 2 or not isinstance(pair[0], str):
                    fail(p.id, 'roles must contain slot/Role pairs')
                slot, role = pair
                collect(roles, role, Role, p.id)
                role_mapping.append((slot, role.id))
            triggers = []
            for t in p.triggers:
                collect(roles, t.actor, Role, t.id)
                if not isinstance(t.mapping, tuple):
                    fail(t.id, 'mapping must be a tuple of Artifact/source pairs')
                mapping = []
                for pair in t.mapping:
                    if not isinstance(pair, tuple) or len(pair) != 2:
                        fail(t.id, 'mapping must contain Artifact/source pairs')
                    artifact, source = pair
                    if not isinstance(artifact, Artifact) or id(artifact) not in artifact_objects:
                        fail(t.id, 'mapping must reference a declared Artifact object')
                    if not isinstance(source, str):
                        fail(t.id, 'input source must be text')
                    mapping.append((artifact.id, source))
                if t.after is not None and id(t.after) not in placement_objects:
                    fail(t.id, 'preceding placement must belong to this workflow')
                if t.wait is not None and not isinstance(t.wait, str):
                    fail(t.id, 'wait must be text')
                compiled = Trigger(t.id, t.name, tuple(mapping), t.after.id if t.after else None, t.wait, t.actor.id)
                triggers.append(compiled)
                compiled_triggers[id(p), id(t)] = compiled
            if p.next_workflow is not None and p.next_workflow not in metadata:
                fail(p.id, 'next workflow must be included in compilation')
            primary = triggers[0]
            bindings[id(p)] = Binding(p.id, p.pipeline.id, primary.name, primary.input_mapping,
                primary.after, primary.wait, metadata[p.next_workflow].id if p.next_workflow else None,
                tuple(triggers[1:]), primary.actor_role_id, tuple(role_mapping), primary.id)
        compiled_workflow = Workflow(options.id, options.name, tuple(bindings.values()))
        compiled_transitions = []
        for t in transitions:
            if id(t.binding) not in bindings:
                fail(t.id, 'binding must reference a placement in this workflow')
            trigger_key = (id(t.binding), id(t.trigger))
            if trigger_key not in compiled_triggers:
                fail(t.id, 'trigger must reference an object belonging to the placement')
            compiled_transitions.append(Transition(t.id, t.name, t.source, t.target,
                bindings[id(t.binding)], compiled_triggers[trigger_key], t.condition))
        workflows.append(compiled_workflow)
        graphs.append(StateGraph(compiled_workflow, initial[0], states, tuple(compiled_transitions)))
    catalog = Catalog(artifacts, tuple(pipelines.values()), tuple(workflows), tuple(roles.values()))
    program = Program.from_catalog(catalog)
    graph_ids = set()
    for graph in graphs:
        graph.validate(catalog)
        for entity in (*graph.states, *graph.transitions):
            if entity.id in graph_ids:
                fail(entity.id, 'graph IDs must be globally unique')
            graph_ids.add(entity.id)
    return CompiledWorkflows(program, tuple(graphs))
