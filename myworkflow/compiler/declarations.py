"""Typed annotations compiled without running business handlers.

Use objects to connect declarations. Stable IDs only identify exported contracts.
"""
from myworkflow.contracts.annotations import Extensible, annotate, declaration
from collections.abc import Callable
from dataclasses import dataclass

from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.models import Artifact, Binding, ContractCatalog, Pipeline, Role, Trigger, Workflow
from myworkflow.compiler.pipelines import Action, Operation, PipelineDeclaration, compile_pipeline
from myworkflow.compiler.program import Program
from myworkflow.contracts.state_graph import State, StateGraph, Transition
from myworkflow.contracts.value_objects import ValueObject, validate_definitions


@dataclass(frozen=True)
class StateDeclaration(State):
    initial: bool = False


@dataclass(frozen=True)
class TriggerDeclaration(Extensible):
    id: str
    name: str
    actor: Role
    mapping: tuple[tuple[Artifact, str], ...] = ()
    after: 'Placement | None' = None
    wait: str | None = None


@dataclass(frozen=True)
class Placement(Extensible):
    id: str
    pipeline: Pipeline | PipelineDeclaration | Callable
    triggers: tuple[TriggerDeclaration, ...]
    roles: tuple[tuple[str, Role], ...]
    next_workflow: Callable | None = None


@dataclass(frozen=True)
class TransitionDeclaration(Extensible):
    id: str
    name: str
    source: StateDeclaration
    target: StateDeclaration
    binding: Placement
    trigger: TriggerDeclaration
    condition: str = ''
    guard: Callable | None = None


@dataclass(frozen=True)
class WorkflowDeclaration(Extensible):
    id: str
    name: str
    members: tuple[object, ...] = ()


@dataclass(frozen=True)
class CompiledWorkflows:
    program: Program
    graphs: tuple[StateGraph, ...]
    declarations: tuple[object, ...] = ()

    def workflow(self, selected) -> Workflow:
        for index, target in enumerate(self.declarations):
            if target is selected:
                return self.program.model.workflows[index]
        raise ContractError("Workflow declaration is not included in this compilation")

    @property
    def catalog(self) -> ContractCatalog:
        return self.program.model


state = StateDeclaration
trigger = TriggerDeclaration
bind = Placement
transition = TransitionDeclaration


def workflow(*, id: str, name: str, members=(), extensions=None):
    return annotate(WorkflowDeclaration(id, name, members, extensions={} if extensions is None else extensions))


def _fail(where, message):
    raise ContractError(f'{where}: {message}')


def _sequence(value, typ, where):
    if not isinstance(value, tuple) or any(not isinstance(v, typ) for v in value):
        _fail(where, f'expected a tuple of {typ.__name__}')


def _workflow_members(declarations):
    if not declarations:
        _fail('workflows', 'at least one class is required')
    if len({id(c) for c in declarations}) != len(declarations):
        _fail('workflows', 'duplicate class')
    metadata = {}
    members = {}
    for cls in declarations:
        if not callable(cls) or not isinstance(declaration(cls), WorkflowDeclaration):
            _fail('workflow', 'expected a workflow annotation')
        if isinstance(cls, type) and cls.__bases__ != (object,):
            _fail(cls.__name__, 'workflow inheritance is not supported')
        options = declaration(cls)
        metadata[cls] = options
        if not isinstance(options.members, tuple):
            _fail(options.id, 'members must be a tuple')
        selected = options.members or tuple(vars(cls).values())
        named = [(index, declaration(value)) for index, value in enumerate(selected)
                 if isinstance(declaration(value), (StateDeclaration, Placement, TransitionDeclaration))]
        if options.members and len(named) != len(selected):
            _fail(options.id, 'members must reference states, placements or transitions')
        if len({id(value) for _, value in named}) != len(named):
            _fail(options.id, 'declaration aliases are not supported')
        members[cls] = tuple(value for _, value in named)

    return metadata, members


def compile_workflows(*declarations: Callable, artifacts: tuple[Artifact, ...] = (),
                      pipelines: tuple[Pipeline | PipelineDeclaration, ...] = (), roles: tuple[Role, ...] = (),
                      value_objects: tuple[ValueObject, ...] = ()) -> CompiledWorkflows:
    """Compile attached declarations without executing annotated functions.

    No methods, properties, generators or handlers are invoked to discover nodes.
    Pipelines and roles are collected from placements, or explicitly ordered.
    Symbolic pipeline references are lowered into the same immutable model as legacy inputs.
    """
    if not isinstance(artifacts, tuple):
        _fail('artifacts', 'expected a tuple')
    artifacts = tuple(declaration(a) for a in artifacts)
    _sequence(artifacts, Artifact, 'artifacts')
    validate_definitions(value_objects)
    definitions = {d.id: d for d in value_objects}
    for artifact in artifacts:
        if artifact.value_object is not None:
            definition = artifact.value_object
            if not isinstance(definition, ValueObject):
                _fail(artifact.id, 'value_object must reference ValueObject')
            if definition.id in definitions and definitions[definition.id] is not definition:
                _fail(definition.id, 'different objects share a value object ID')
            definitions[definition.id] = definition
    if len({id(a) for a in artifacts}) != len(artifacts):
        _fail('artifacts', 'duplicate declaration')
    metadata, members = _workflow_members(declarations)

    declared_pipelines, declared_roles = pipelines, roles
    if not isinstance(declared_pipelines, tuple) or not isinstance(declared_roles, tuple):
        _fail('catalog', 'pipelines and roles must be tuples')
    if len({id(p) for p in declared_pipelines}) != len(declared_pipelines) or len({id(r) for r in declared_roles}) != len(declared_roles):
        _fail('catalog', 'duplicate explicit pipeline or role declaration')
    pipelines, roles = {}, {}
    lowered = {}
    artifact_objects = {id(a) for a in artifacts}

    def collect(target, obj, typ, where):
        obj = declaration(obj)
        if not isinstance(obj, typ):
            _fail(where, f'expected {"Pipeline" if isinstance(typ, tuple) else typ.__name__} reference')
        if obj.id in target and target[obj.id] is not obj:
            _fail(where, f'{obj.id}: different objects share a stable ID')
        target[obj.id] = obj
        return obj

    for pipeline in declared_pipelines:
        collect(pipelines, pipeline, (Pipeline, PipelineDeclaration), 'pipelines')
    for role in declared_roles:
        collect(roles, role, Role, 'roles')
    workflows, graphs = [], []
    for cls in declarations:
        options = metadata[cls]
        values = members[cls]
        states = tuple(v for v in values if isinstance(v, StateDeclaration))
        placements = tuple(v for v in values if isinstance(v, Placement))
        transitions = tuple(v for v in values if isinstance(v, TransitionDeclaration))
        if any(type(s.initial) is not bool for s in states):
            _fail(options.id, 'initial must be boolean')
        initial = [s for s in states if s.initial]
        if (states or transitions) and len(initial) != 1:
            _fail(options.id, 'exactly one initial state is required')
        placement_objects = {id(p) for p in placements}
        bindings = {}
        compiled_triggers = {}
        for p in placements:
            pipeline = collect(pipelines, p.pipeline, (Pipeline, PipelineDeclaration), p.id)
            if not isinstance(p.triggers, tuple):
                _fail(p.id, 'triggers must be a tuple')
            trigger_specs = tuple(declaration(t) for t in p.triggers)
            _sequence(trigger_specs, TriggerDeclaration, p.id + '.triggers')
            if not trigger_specs or len({id(t) for t in trigger_specs}) != len(trigger_specs):
                _fail(p.id, 'at least one distinct trigger is required')
            if not isinstance(p.roles, tuple):
                _fail(p.id, 'roles must be a tuple of slot/Role pairs')
            role_mapping = []
            for pair in p.roles:
                if not isinstance(pair, tuple) or len(pair) != 2 or not isinstance(pair[0], str):
                    _fail(p.id, 'roles must contain slot/Role pairs')
                slot, role = pair
                role = collect(roles, role, Role, p.id)
                role_mapping.append((slot, role.id))
            triggers = []
            for t in trigger_specs:
                actor = collect(roles, t.actor, Role, t.id)
                if not isinstance(t.mapping, tuple):
                    _fail(t.id, 'mapping must be a tuple of Artifact/source pairs')
                mapping = []
                for pair in t.mapping:
                    if not isinstance(pair, tuple) or len(pair) != 2:
                        _fail(t.id, 'mapping must contain Artifact/source pairs')
                    artifact, source = pair
                    artifact = declaration(artifact)
                    if not isinstance(artifact, Artifact) or id(artifact) not in artifact_objects:
                        _fail(t.id, 'mapping must reference a declared Artifact object')
                    if not isinstance(source, str):
                        _fail(t.id, 'input source must be text')
                    mapping.append((artifact.id, source))
                after = declaration(t.after)
                if after is not None and id(after) not in placement_objects:
                    _fail(t.id, 'preceding placement must belong to this workflow')
                if t.wait is not None and not isinstance(t.wait, str):
                    _fail(t.id, 'wait must be text')
                compiled = Trigger(t.id, t.name, tuple(mapping), after.id if after else None, t.wait, actor.id, extensions=t.extensions)
                triggers.append(compiled)
                compiled_triggers[id(p), id(t)] = compiled
            if p.next_workflow is not None and p.next_workflow not in metadata:
                _fail(p.id, 'next workflow must be included in compilation')
            bindings[id(p)] = Binding(p.id, pipeline.id, tuple(triggers), tuple(role_mapping),
                metadata[p.next_workflow].id if p.next_workflow else None, extensions=p.extensions)
        compiled_workflow = Workflow(options.id, options.name, tuple(bindings.values()), extensions=options.extensions)
        compiled_transitions = []
        for t in transitions:
            binding, requested = declaration(t.binding), declaration(t.trigger)
            if id(binding) not in bindings:
                _fail(t.id, 'binding must reference a placement in this workflow')
            trigger_key = (id(binding), id(requested))
            if trigger_key not in compiled_triggers:
                _fail(t.id, 'trigger must reference an object belonging to the placement')
            compiled_transitions.append(Transition(t.id, t.name, declaration(t.source), declaration(t.target),
                bindings[id(binding)], compiled_triggers[trigger_key], t.condition, t.guard, extensions=t.extensions))
        workflows.append(compiled_workflow)
        if states or transitions:
            graphs.append(StateGraph(compiled_workflow, initial[0], states, tuple(compiled_transitions)))
    operations = {}
    for identity, pipeline in pipelines.items():
        if isinstance(pipeline, PipelineDeclaration):
            for selected in pipeline.steps:
                step = declaration(selected)
                if isinstance(step, Action) and step.compensate is not None:
                    collect(operations, step.compensate, Operation, step.id)
        lowered[identity] = compile_pipeline(pipeline, artifacts) if isinstance(pipeline, PipelineDeclaration) else pipeline
    catalog = ContractCatalog(artifacts, tuple(lowered.values()), tuple(workflows), tuple(roles.values()), tuple(definitions.values()))
    program = Program.from_catalog(catalog)
    graph_ids = set()
    for graph in graphs:
        graph.validate(catalog)
        for entity in (*graph.states, *graph.transitions):
            if entity.id in graph_ids:
                _fail(entity.id, 'graph IDs must be globally unique')
            graph_ids.add(entity.id)
    return CompiledWorkflows(program, tuple(graphs), declarations)
