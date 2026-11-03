"""Compatibility dictionary export for an already compiled catalog."""
from myworkflow.contracts.annotations import extension_fields
from myworkflow.contracts.models import ContractCatalog, Lock


def catalog_to_spec(catalog: ContractCatalog) -> dict:
    """Serialize references; this export is never the typed declarations' source."""
    result = {
        **({'id': catalog.id, 'name': catalog.name} if catalog.id else {}),
        **({'value_objects': [d.definition() for d in catalog.value_objects]} if catalog.value_objects else {}),
        'roles': [{'id': r.id, 'name': r.name, 'display_name': r.display_name} for r in catalog.roles],
        'artifacts': [{'id': a.id, 'name': a.name, 'key': a.key, 'type': a.type, **({'value_object': a.value_object.id} if a.value_object else {})} for a in catalog.artifacts],
        'pipelines': [{
            'id': p.id, 'name': p.name, 'inputs': list(p.inputs), 'outputs': list(p.outputs), 'reply': p.reply,
            'steps': [{
                'id': s.id, 'name': s.name, 'kind': 'lock', 'reads': list(s.keys),
                'namespace': s.namespace, 'timeout': s.timeout, 'conflict': s.conflict,
                'scope': s.scope, 'actor': s.actor,
            } if isinstance(s, Lock) else {
                'id': s.id, 'name': s.name, 'kind': s.kind, 'summary': s.summary, 'actor': s.actor,
                'reads': list(s.reads), 'writes': list(s.writes),
                'uses': [[u.artifact_id, u.operation] for u in s.uses],
                'when': list(s.when) if s.when else None, 'attempts': s.attempts, 'compensate': s.compensate,
            } for s in p.steps],
        } for p in catalog.pipelines],
        'workflows': [{
            'id': w.id, 'name': w.name, 'bindings': [{
                'id': b.id, 'pipeline': b.pipeline_id, 'role_mapping': dict(b.role_mapping),
                'next_workflow': b.next_workflow_id,
                'triggers': [{
                    'id': t.id, 'name': t.name, 'mapping': dict(t.input_mapping),
                    'role': t.actor_role_id, 'after': t.after, 'wait': t.wait,
                } for t in b.triggers],
            } for b in w.bindings],
        } for w in catalog.workflows],
    }
    for entities, records in ((catalog.roles, result['roles']), (catalog.artifacts, result['artifacts']),
                              (catalog.pipelines, result['pipelines']), (catalog.workflows, result['workflows'])):
        for entity, record in zip(entities, records, strict=True):
            record.update(extension_fields(entity))
    for pipeline, record in zip(catalog.pipelines, result['pipelines'], strict=True):
        for step, data in zip(pipeline.steps, record['steps'], strict=True):
            data.update(extension_fields(step))
    for workflow, record in zip(catalog.workflows, result['workflows'], strict=True):
        for binding, data in zip(workflow.bindings, record['bindings'], strict=True):
            data.update(extension_fields(binding))
            for trigger, item in zip(binding.triggers, data['triggers'], strict=True):
                item.update(extension_fields(trigger))
    return {**result, **extension_fields(catalog)}
