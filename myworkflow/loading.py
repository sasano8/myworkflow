"""Parse the external dictionary once into immutable domain declarations."""
from myworkflow.models import Artifact, Binding, Catalog, Lock, Pipeline, Role, Step, Trigger, Use, Workflow
from myworkflow.errors import ContractError


def load_catalog(spec, *, value_objects=()):
    location = 'contract'
    try:
        def items(container, key):
            value = container[key]
            if not isinstance(value, (list, tuple)):
                raise ContractError(f'{location}.{key}: expected a sequence')
            return value

        def strings(container, key):
            result = tuple(items(container, key))
            if any(not isinstance(v, str) for v in result) or len(set(result)) != len(result):
                raise ContractError(f'{location}.{key}: expected unique string references')
            return result

        from myworkflow.value_objects import validate_definitions
        validate_definitions(value_objects)
        definitions = {d.id: d for d in value_objects}
        if spec.get('value_objects', []) != [d.definition() for d in value_objects]:
            raise ContractError('Value object definitions require matching explicit Python declarations; no dynamic imports')
        artifacts = tuple(Artifact(a['id'], a['name'], a['key'], a['type'],
                                   definitions[a['value_object']] if 'value_object' in a else None) for a in items(spec, 'artifacts'))
        roles = tuple(Role(r['id'], r['name'], r['display_name']) for r in items(spec, 'roles'))
        pipelines = []
        for p in items(spec, 'pipelines'):
            location = p.get('id', 'pipeline')
            steps = []
            for s in items(p, 'steps'):
                location = s.get('id', location + '.steps')
                kind = s['kind']
                if kind == 'lock':
                    expected_conflict = '待機' if s.get('timeout', 0) else '拒否'
                    if s.get('conflict', expected_conflict) != expected_conflict:
                        raise ContractError(f'{location}.conflict: policy must match the configured timeout')
                    if s.get('writes') or s.get('when'):
                        raise ContractError(f'{location}: lock cannot be conditional or write artifacts')
                    steps.append(Lock(s['id'], s['name'], strings(s, 'reads'), conflict=s.get('conflict', '待機' if s.get('timeout', 0) else '拒否'), namespace=s.get('namespace', 'business'), timeout=s.get('timeout', 0), scope=s.get('scope', 'パイプライン終了まで（異常終了を含む）'), actor=s.get('actor', 'system')))
                elif kind == 'action':
                    condition = s.get('when')
                    if condition is not None and (not isinstance(condition, (list, tuple)) or len(condition) != 2 or not isinstance(condition[0], str) or type(condition[1]) is not bool):
                        raise ContractError(f'{location}.when: expected [artifact ID, boolean]')
                    steps.append(Step(s['id'], s['name'], s['summary'],
                        tuple(Use(*u) for u in s.get('uses', ())), s.get('actor', 'system'),
                        strings(s, 'reads'), strings(s, 'writes'), tuple(condition) if condition is not None else None,
                        s.get('attempts', 1), s.get('compensate')))
                else:
                    raise ContractError(f'{location}.kind: unknown step kind {kind}')
            location = p['id']
            if type(p['reply']) is not bool:
                raise ContractError(f'{location}.reply: expected bool')
            pipelines.append(Pipeline(p['id'], p['name'], strings(p, 'inputs'), strings(p, 'outputs'), tuple(steps), p['reply']))
        workflows = []
        for w in items(spec, 'workflows'):
            bindings = []
            for b in items(w, 'bindings'):
                location = b.get('id', 'binding')
                triggers = []
                for t in items(b, 'triggers'):
                    location = t.get('id', location + '.trigger')
                    if not isinstance(t['mapping'], dict):
                        raise ContractError(f'{location}.mapping: expected an object')
                    triggers.append(Trigger(t['id'], t['name'], tuple(t['mapping'].items()), t.get('after'), t.get('wait'), t['role']))
                if not triggers:
                    raise ContractError(f'{b["id"]}.triggers: at least one is required')
                primary = triggers[0]
                bindings.append(Binding(b['id'], b['pipeline'], primary.name, primary.input_mapping,
                    primary.after, primary.wait, b.get('next_workflow'), tuple(triggers[1:]), primary.actor_role_id,
                    tuple((key, value) for key, value in b.get('role_mapping', {'system': 'role.system'}).items()), primary.id))
            workflows.append(Workflow(w['id'], w['name'], tuple(bindings)))
        model = Catalog(artifacts, tuple(pipelines), tuple(workflows), roles, value_objects)
        entities = [*artifacts, *roles, *pipelines, *workflows]
        entities += [s for p in pipelines for s in p.steps]
        entities += [b for w in workflows for b in w.bindings]
        entities += [t for b in [b for w in workflows for b in w.bindings] for t in b.triggers]
        for entity in entities:
            if not isinstance(entity.id, str) or not isinstance(entity.name if hasattr(entity, 'name') else entity.trigger, str):
                raise ContractError(f'{location}: IDs and names must be strings')
        for artifact in artifacts:
            if not isinstance(artifact.key, str) or not isinstance(artifact.type, str):
                raise ContractError(f'{artifact.id}: key and type must be strings')
        for step in [s for p in pipelines for s in p.steps]:
            if isinstance(step, Step) and (not isinstance(step.summary, str) or not isinstance(step.actor, str) or (step.compensate is not None and not isinstance(step.compensate, str))):
                raise ContractError(f'{step.id}: invalid summary, actor or compensation reference')
        for role in roles:
            if not isinstance(role.display_name, str):
                raise ContractError(f'{role.id}.display_name: expected string')
        for b in [b for w in workflows for b in w.bindings]:
            if not isinstance(b.pipeline_id, str) or (b.next_workflow_id is not None and not isinstance(b.next_workflow_id, str)):
                raise ContractError(f'{b.id}: invalid pipeline or workflow reference')
            for t in b.triggers:
                if not isinstance(t.actor_role_id, str):
                    raise ContractError(f'{t.id}.role: expected a role ID')
                if any(not isinstance(k, str) or not isinstance(v, str) for k, v in t.input_mapping):
                    raise ContractError(f'{t.id}.mapping: keys and values must be strings')
        return model
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError(f'{location}: invalid contract structure ({exc})') from exc
