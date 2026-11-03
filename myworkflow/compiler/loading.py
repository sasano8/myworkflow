"""Parse the external dictionary once into immutable domain declarations."""
from myworkflow.contracts.models import Artifact, Binding, ContractCatalog, Lock, Pipeline, Role, Step, Trigger, Use, Workflow
from myworkflow.contracts.errors import ContractError


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

        from myworkflow.contracts.value_objects import validate_definitions
        validate_definitions(value_objects)
        definitions = {d.id: d for d in value_objects}
        if spec.get('value_objects', []) != [d.definition() for d in value_objects]:
            raise ContractError('Value object definitions require matching explicit Python declarations; no dynamic imports')
        artifacts = tuple(Artifact(a['id'], a['name'], a['key'], a['type'],
                                   definitions[a['value_object']] if 'value_object' in a else None, extensions=a.get('extensions', {})) for a in items(spec, 'artifacts'))
        roles = tuple(Role(r['id'], r['name'], r['display_name'], extensions=r.get('extensions', {})) for r in items(spec, 'roles'))
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
                    steps.append(Lock(s['id'], s['name'], strings(s, 'reads'), conflict=s.get('conflict', '待機' if s.get('timeout', 0) else '拒否'), namespace=s.get('namespace', 'business'), timeout=s.get('timeout', 0), scope=s.get('scope', 'パイプライン終了まで（異常終了を含む）'), actor=s.get('actor', 'system'), extensions=s.get('extensions', {})))
                elif kind == 'action':
                    condition = s.get('when')
                    if condition is not None and (not isinstance(condition, (list, tuple)) or len(condition) != 2 or not isinstance(condition[0], str) or type(condition[1]) is not bool):
                        raise ContractError(f'{location}.when: expected [artifact ID, boolean]')
                    steps.append(Step(s['id'], s['name'], s['summary'],
                        tuple(Use(*u) for u in s.get('uses', ())), s.get('actor', 'system'),
                        strings(s, 'reads'), strings(s, 'writes'), tuple(condition) if condition is not None else None,
                        s.get('attempts', 1), s.get('compensate'), extensions=s.get('extensions', {})))
                else:
                    raise ContractError(f'{location}.kind: unknown step kind {kind}')
            location = p['id']
            if type(p['reply']) is not bool:
                raise ContractError(f'{location}.reply: expected bool')
            pipelines.append(Pipeline(p['id'], p['name'], strings(p, 'inputs'), strings(p, 'outputs'), tuple(steps), p['reply'], extensions=p.get('extensions', {})))
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
                    triggers.append(Trigger(t['id'], t['name'], tuple(t['mapping'].items()), t.get('after'), t.get('wait'), t['role'], extensions=t.get('extensions', {})))
                if not triggers:
                    raise ContractError(f'{b["id"]}.triggers: at least one is required')
                bindings.append(Binding(b['id'], b['pipeline'], tuple(triggers),
                    tuple(b.get('role_mapping', {'system': 'role.system'}).items()), b.get('next_workflow'), extensions=b.get('extensions', {})))
            workflows.append(Workflow(w['id'], w['name'], tuple(bindings), extensions=w.get('extensions', {})))
        model = ContractCatalog(artifacts, tuple(pipelines), tuple(workflows), roles, value_objects, id=spec.get('id', ''), name=spec.get('name', ''), extensions=spec.get('extensions', {}))
        for entity in model.entities:
            if not isinstance(entity.id, str) or (hasattr(entity, 'name') and not isinstance(entity.name, str)):
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
