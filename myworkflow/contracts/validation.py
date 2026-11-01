"""Structural and semantic contract checks."""
from myworkflow.contracts.models import Lock, Trigger
from myworkflow.contracts.value_objects import validate_definitions


def validate_catalog(catalog):
    validate_definitions(catalog.value_objects)
    entities = [*catalog.artifacts, *catalog.pipelines, *catalog.workflows, *catalog.roles, *catalog.value_objects]
    entities += [s for p in catalog.pipelines for s in p.steps]
    entities += [b for w in catalog.workflows for b in w.bindings]
    entities += [t for w in catalog.workflows for b in w.bindings for t in b.additional_triggers]
    ids = [e.id for e in entities]
    if any(not i.strip() for i in ids) or len(ids) != len(set(ids)):
        raise ValueError("IDs must be nonempty and globally unique")
    roles = {r.id for r in catalog.roles}
    if any(not r.name.strip() or not r.display_name.strip() for r in catalog.roles):
        raise ValueError("Role names must be nonempty")
    artifacts = {a.id for a in catalog.artifacts}
    pipelines = {p.id: p for p in catalog.pipelines}
    workflows = {w.id for w in catalog.workflows}
    for a in catalog.artifacts:
        if a.value_object is not None and not any(a.value_object is d for d in catalog.value_objects):
            raise ValueError(f'{a.id}: value object must belong to catalog')
    for p in catalog.pipelines:
        if type(p.reply) is not bool:
            raise ValueError("Pipeline reply must be boolean")
        refs = list(p.inputs + p.outputs)
        for s in p.steps:
            if isinstance(s, Lock):
                if not s.keys:
                    raise ValueError("Lock requires context keys")
                refs.extend(s.keys)
            else:
                if not s.summary.strip():
                    raise ValueError("Step requires a business summary")
                for u in s.uses:
                    if u.operation not in {"参照", "保持", "DB読取", "DB作成", "DB更新", "送信"}:
                        raise ValueError("Unknown artifact operation")
                    refs.append(u.artifact_id)
        if set(refs) - artifacts:
            raise ValueError("Unknown artifact reference")
    for w in catalog.workflows:
        placements = {b.id for b in w.bindings}
        for b in w.bindings:
            if b.pipeline_id not in pipelines:
                raise ValueError("Unknown pipeline reference")
            mapping = dict(b.role_mapping)
            required = {"system", *(s.actor for s in pipelines[b.pipeline_id].steps)}
            if len(mapping) != len(b.role_mapping) or set(mapping) != required:
                raise ValueError("Role mapping must cover pipeline role slots exactly")
            if set(mapping.values()) - roles:
                raise ValueError("Unknown mapped role")
            triggers = (Trigger(b.id, b.trigger, b.input_mapping, b.after, b.wait, b.actor_role_id), *b.additional_triggers)
            for t in triggers:
                if t.actor_role_id not in roles:
                    raise ValueError("Unknown trigger actor role")
                mapped = [target for target, source in t.input_mapping]
                if len(mapped) != len(set(mapped)) or set(mapped) != set(pipelines[b.pipeline_id].inputs):
                    raise ValueError("Input mapping must cover the pipeline contract exactly")
                if not t.name.strip() or any(not source.strip() for _, source in t.input_mapping):
                    raise ValueError("Trigger and input sources must be described")
                if t.after is not None and (t.after not in placements or t.after == b.id):
                    raise ValueError("Unknown or self-referencing preceding placement")
            if b.next_workflow_id is not None and b.next_workflow_id not in workflows:
                raise ValueError("Unknown next workflow reference")
