"""Compile Python declarations into a deterministic IR and reviewable target outputs."""
from myworkflow.generation.documents import document_program
from dataclasses import dataclass, replace
from collections.abc import Callable
from myworkflow.contracts.state_graph import StateGraph
import hashlib
import inspect
import json
from pathlib import Path

from myworkflow.generation.interfaces import interfaces_source
from myworkflow.compiler.declarations import CompiledWorkflows
from myworkflow.contracts.errors import ContractError
from myworkflow.generation.files import write_outputs
from myworkflow.contracts.models import ContractCatalog
from myworkflow.compiler.program import Program
from myworkflow.generation.business import export_business
from myworkflow.runtime.registry import Registry
from myworkflow.generation.state_tables import render_state_graph
from myworkflow.generation.flowcharts import render_business_flow


@dataclass(frozen=True)
class BuildConfig:
    compiled: CompiledWorkflows
    registry: Registry
    required_features: tuple[str, ...] = ()
    document_renderer: Callable[[Program, tuple[StateGraph, ...], Registry], str] | None = None
    extension_encoder: Callable[[object], object] | None = None


class BuildError(ValueError):
    pass


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def _yaml(value, indent=0):
    """A small emitter for JSON-compatible values, not a YAML parser or templating engine."""
    pad = ' ' * indent
    scalar = lambda v: json.dumps(v, ensure_ascii=False, allow_nan=False)
    if isinstance(value, dict) and value:
        lines = []
        for key, child in value.items():
            if isinstance(child, (dict, list)) and child:
                lines.append(pad + scalar(key) + ':')
                lines.append(_yaml(child, indent + 2))
            else:
                lines.append(pad + scalar(key) + ': ' + scalar(child))
        return '\n'.join(lines)
    if isinstance(value, list) and value:
        lines = []
        for child in value:
            if isinstance(child, (dict, list)) and child:
                lines.extend((pad + '-', _yaml(child, indent + 2)))
            else:
                lines.append(pad + '- ' + scalar(child))
        return '\n'.join(lines)
    return pad + scalar(value)


def compile_outputs(config: BuildConfig, *, target: str, workflows: tuple[str, ...] = ()) -> dict[str, str]:
    """Validate before producing outputs. No network, deployment or handler execution."""
    if target not in ('temporal', 'kestra'):
        raise BuildError(f'Unknown target: {target}')
    if not isinstance(config, BuildConfig):
        raise BuildError('Build module must expose BUILD: BuildConfig')
    for name in ('document_renderer', 'extension_encoder'):
        if getattr(config, name) is not None and not callable(getattr(config, name)):
            raise BuildError(f'{name} must be callable')
    if not isinstance(config.required_features, tuple) or any(not isinstance(f, str) for f in config.required_features):
        raise BuildError('required_features must be a tuple of feature names')
    unsupported = set(config.required_features) - {'python_pipeline'}
    if unsupported:
        raise BuildError(f'Unsupported required features: {sorted(unsupported)}')
    original = config.compiled.catalog
    known = {w.id for w in original.workflows}
    if set(workflows) - known:
        raise BuildError(f'Unknown workflows: {sorted(set(workflows) - known)}')
    selected = tuple(w for w in original.workflows if not workflows or w.id in workflows)
    identities = {w.id for w in selected}
    graphs = tuple(g for g in config.compiled.graphs if g.workflow.id in identities)
    errors = []
    for workflow in selected:
        for binding in workflow.bindings:
            location = f'{workflow.id}/{binding.id}'
            if binding.next_workflow_id and binding.next_workflow_id not in identities:
                errors.append(f'{location}: next workflow is outside the explicit selection')
            if target == 'kestra':
                if binding.next_workflow_id:
                    errors.append(f'{location}: next_workflow is not supported by the Kestra preview')
                for trigger in binding.triggers:
                    if trigger.wait is not None:
                        errors.append(f'{location}/{trigger.id}: wait is not supported by the Kestra preview')
                    if trigger.after is not None:
                        errors.append(f'{location}/{trigger.id}: after is not supported by the Kestra preview')
    if target == 'kestra':
        errors.extend(f'{g.workflow.id}: state graph execution is not supported by the Kestra preview' for g in graphs)
    if errors:
        raise BuildError('\n'.join(errors))
    used_pipelines = {b.pipeline_id for w in selected for b in w.bindings}
    model = replace(original, pipelines=tuple(p for p in original.pipelines if p.id in used_pipelines), workflows=selected)
    program = Program.from_catalog(model)
    program.check(config.registry)
    for graph in graphs:
        graph.validate(model)
    implementations = {identity: f'{fn.__module__}:{fn.__qualname__}'
                       for identity, fn in sorted(config.registry.handlers.items())
                       if identity in program.implementation_ids}
    ir = {'schema_version': 1, 'business': export_business(program, extension_encoder=config.extension_encoder),
          'handlers': [program.handler(b.id, t.id).to_dict() for b in program.bindings.values() for t in b.triggers],
          'state_graphs': [g.to_dict(model, extension_encoder=config.extension_encoder) for g in graphs], 'implementations': implementations}
    if config.document_renderer is None:
        documentation = document_program(program, config.registry)
        for graph in graphs:
            documentation += '\n' + render_business_flow(graph, model) + '\n' + render_state_graph(graph, model)
    else:
        documentation = config.document_renderer(program, graphs, config.registry)
        if not isinstance(documentation, str):
            raise BuildError('document_renderer must return a string')
    outputs = {'ir.json': _json(ir), 'requirements.md': documentation, 'interfaces.py': interfaces_source(program)}
    if model.value_objects:
        from myworkflow.generation.data_definitions import data_definitions_source, render_data_definitions
        outputs['data-definitions.json'] = data_definitions_source(model, extension_encoder=config.extension_encoder)
        outputs['data-definitions.md'] = render_data_definitions(model, extension_encoder=config.extension_encoder)
    if target == 'kestra':
        manifest = {'format': 'myworkflow.kestra.preview/v1', 'target': 'kestra', 'deployable': False,
                    'execution_model': 'application-supplied-python-pipeline', 'ir': 'ir.json', 'workflows': []}
        for workflow in selected:
            entries = []
            for binding in workflow.bindings:
                for trigger in binding.triggers:
                    entries.append({'binding': binding.id, 'trigger': trigger.id, 'actor_role': trigger.actor_role_id,
                                    'input_mapping': dict(trigger.input_mapping),
                                    'invoke': {'pipeline': binding.pipeline_id, 'completion': 'PipelineResult'}})
            manifest['workflows'].append({'id': workflow.id, 'name': workflow.name, 'entrypoints': entries})
        outputs['manifest.yaml'] = '# Generated preview. This is not a deployable Kestra Flow.\n' + _yaml(manifest) + '\n'
    outputs['build.json'] = _json({'schema_version': 1, 'target': target,
                                  'mode': 'preview' if target == 'kestra' else 'application-owned-code',
                                  'workflows': [w.id for w in selected],
                                  'files': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in outputs.items()}})
    return outputs


def build(config: BuildConfig, directory, *, target: str, workflows=(), check=False, protected=()):
    outputs = compile_outputs(config, target=target, workflows=tuple(workflows))
    directory = Path(directory)
    if target == 'temporal' and (directory / 'manifest.yaml').exists():
        raise BuildError('Output contains a Kestra manifest; use a separate output directory for Temporal')
    value_sources = [inspect.getsourcefile(d.model) for d in config.compiled.catalog.value_objects]
    implementation_sources = [inspect.getsourcefile(fn) for fn in config.registry.handlers.values()]
    write_outputs({directory / name: text for name, text in outputs.items()}, check=check,
                  protected=(*protected, *(path for path in (*implementation_sources, *value_sources) if path)))
    return outputs
