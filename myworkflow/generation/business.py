"""Machine-readable business output; generated from declarations, never Program.spec."""
from myworkflow.contracts.annotations import extension_fields
from myworkflow.contracts.models import Lock
from myworkflow.contracts.results import DEFAULT_ERROR_CODE
from myworkflow.contracts.names import class_name


COMPLETION = {
    'interface': 'PipelineResult', 'success_code': 0, 'default_error_code': DEFAULT_ERROR_CODE,
    'fields': {'code': 'int', 'messages': 'tuple[Message, ...]'},
    'message_levels': ['info', 'warning', 'error', 'critical'],
}

SECTIONS = ('roles', 'artifacts', 'pipelines', 'steps', 'workflows', 'bindings', 'triggers')


def export_business(program, *, extension_encoder=None):
    model = program.model
    from copy import deepcopy
    result = {'schema_version': 2, 'completion': deepcopy(COMPLETION), **{name: {} for name in SECTIONS}}
    if model.value_objects:
        result['value_objects'] = {d.id: {k: v for k, v in d.definition(extension_encoder=extension_encoder).items() if k != 'id'} for d in model.value_objects}
    for role in model.roles:
        result['roles'][role.id] = {'name': role.name, 'display_name': role.display_name}
    for artifact in model.artifacts:
        result['artifacts'][artifact.id] = {'name': artifact.name, 'key': artifact.key, 'type': artifact.type,
            **({'value_object': artifact.value_object.id} if artifact.value_object else {})}
    for pipeline in model.pipelines:
        result['pipelines'][pipeline.id] = {'name': pipeline.name, 'inputs': list(pipeline.inputs),
            'produces': list(pipeline.outputs), 'reply': pipeline.reply,
            'request_interface': class_name(pipeline.id) + 'Request', 'response_interface': class_name(pipeline.id) + 'Response', 'steps': [s.id for s in pipeline.steps]}
        for step in pipeline.steps:
            if isinstance(step, Lock):
                result['steps'][step.id] = {'name': step.name, 'kind': 'lock', 'reads': list(step.keys),
                    'namespace': step.namespace, 'timeout': step.timeout, 'conflict': step.conflict, 'scope': step.scope}
            else:
                result['steps'][step.id] = {'name': step.name, 'kind': 'action', 'summary': step.summary,
                    'actor': step.actor, 'reads': list(step.reads), 'writes': list(step.writes),
                    'uses': [[u.artifact_id, u.operation] for u in step.uses],
                    'when': list(step.when) if step.when else None, 'attempts': step.attempts, 'compensate': step.compensate}
    for workflow in model.workflows:
        result['workflows'][workflow.id] = {'name': workflow.name, 'bindings': [b.id for b in workflow.bindings]}
        for binding in workflow.bindings:
            result['bindings'][binding.id] = {'pipeline': binding.pipeline_id,
                'triggers': [t.id for t in binding.triggers], 'next_workflow': binding.next_workflow_id,
                'role_mapping': dict(binding.role_mapping)}
            for trigger in binding.triggers:
                result['triggers'][trigger.id] = {'name': trigger.name, 'mapping': dict(trigger.input_mapping),
                    'role': trigger.actor_role_id, 'after': trigger.after, 'wait': trigger.wait}
    entities = {e.id: e for e in model.entities}
    for section in SECTIONS:
        for identity, fields in result.get(section, {}).items():
            fields.update(extension_fields(entities[identity], extension_encoder))
    return {**result, **extension_fields(model, extension_encoder)}


def business_to_spec(document):
    """Convert the reviewed output format into the existing interface generator input."""
    if document.get('schema_version') != 2 or type(document.get('schema_version')) is not int:
        raise ValueError('Unsupported business document schema')
    if set(document) != {'schema_version', 'completion', *SECTIONS, *(key for key in ('value_objects', 'extensions') if key in document)} or any(not isinstance(document[k], dict) for k in SECTIONS):
        raise ValueError('Business document must contain exactly the supported sections')
    if 'value_objects' in document and not isinstance(document['value_objects'], dict):
        raise ValueError('value_objects must be an object')
    from myworkflow._internal.json_values import same
    if not same(document['completion'], COMPLETION):
        raise ValueError('Unsupported completion contract')
    def declarations(section):
        for identity, values in document[section].items():
            if not isinstance(values, dict) or 'id' in values:
                raise ValueError(f'{section}/{identity}: fields must be an object without a duplicate id')
            yield {'id': identity, **values}
    steps = dict((s['id'], s) for s in declarations('steps'))
    triggers = dict((t['id'], t) for t in declarations('triggers'))
    bindings = dict((b['id'], b) for b in declarations('bindings'))
    try:
        pipelines = [{**{k: v for k, v in p.items() if k != 'produces'}, 'outputs': p['produces'],
                      'steps': [steps[s] for s in p['steps']]} for p in declarations('pipelines')]
        workflows = [{**w, 'bindings': [{**bindings[b], 'triggers': [triggers[t] for t in bindings[b]['triggers']]}
                                     for b in w['bindings']]} for w in declarations('workflows')]
    except (KeyError, TypeError) as exc:
        raise ValueError(f'Broken business document reference: {exc}') from exc
    used_steps = [s for p in document['pipelines'].values() for s in p['steps']]
    used_bindings = [b for w in document['workflows'].values() for b in w['bindings']]
    used_triggers = [t for b in document['bindings'].values() for t in b['triggers']]
    for section, used in [('steps', used_steps), ('bindings', used_bindings), ('triggers', used_triggers)]:
        if set(used) != set(document[section]) or len(used) != len(set(used)):
            raise ValueError(f'{section}: unreferenced or multiply owned definitions')
    return {**({'extensions': document['extensions']} if 'extensions' in document else {}), **({'value_objects': list(declarations('value_objects'))} if 'value_objects' in document else {}),
            'roles': list(declarations('roles')), 'artifacts': list(declarations('artifacts')),
            'pipelines': pipelines, 'workflows': workflows}
