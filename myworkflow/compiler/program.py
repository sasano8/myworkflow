from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.identity import definition_id
from myworkflow.contracts.models import Step

from myworkflow.contracts.value_objects import PRIMITIVES as TYPES

class Program:
    def __init__(self, spec, *, value_objects=()):
        import json
        from myworkflow.compiler.loading import load_catalog
        self.model = load_catalog(spec, value_objects=value_objects)
        try:
            self._source_json = json.dumps(spec, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ContractError(f'contract: only serializable declarations are accepted ({exc})') from exc
        self._index()

    @classmethod
    def from_catalog(cls, catalog):
        """Use typed declarations directly, retaining object identity for graph references."""
        from myworkflow.contracts.models import ContractCatalog
        if not isinstance(catalog, ContractCatalog):
            raise ContractError('contract: expected ContractCatalog')
        from dataclasses import fields, is_dataclass
        def immutable(value, path):
            if is_dataclass(value) and not isinstance(value, type):
                for field in fields(value):
                    if field.name != 'extensions':
                        immutable(getattr(value, field.name), path + '.' + field.name)
            elif isinstance(value, tuple):
                for index, item in enumerate(value):
                    immutable(item, f'{path}[{index}]')
            elif isinstance(value, type):
                from pydantic import BaseModel
                if not issubclass(value, BaseModel):
                    raise ContractError(f'{path}: only Pydantic model classes are accepted')
            elif type(value) not in (str, int, float, bool, type(None)):
                raise ContractError(f'{path}: typed declarations must contain immutable values')
        immutable(catalog, 'catalog')
        result = cls.__new__(cls)
        result.model = catalog
        # Validate before export so invalid duplicate references cannot disappear in dicts.
        result._index()
        result._source_json = None
        return result

    def _index(self):
        from types import MappingProxyType
        self.artifacts = MappingProxyType({a.id: a for a in self.model.artifacts})
        self.plans = MappingProxyType({p.id: p for p in self.model.pipelines})
        self.bindings = MappingProxyType({b.id: b for w in self.model.workflows for b in w.bindings})
        self.steps = MappingProxyType({s.id: s for p in self.model.pipelines for s in p.steps})
        self.processing_steps = tuple(s for s in self.steps.values() if isinstance(s, Step))
        self.implementation_ids = frozenset(identity for s in self.processing_steps for identity in (s.id, s.compensate) if identity)
        self.validate()

    @property
    def spec(self):
        """Compatibility snapshot; mutating it never changes the compiled model."""
        import json
        if self._source_json is None:
            from myworkflow.compiler.serialization import catalog_to_spec
            self._source_json = json.dumps(catalog_to_spec(self.model), ensure_ascii=False)
        return json.loads(self._source_json)

    def validate(self):
        from myworkflow.compiler.validation import validate_program
        try:
            validate_program(self)
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            if isinstance(exc, ContractError):
                raise
            raise ContractError(f'contract: {exc}') from exc

    def catalog(self):
        return self.model

    def binding(self, identity):
        identity = definition_id(identity)
        try:
            return self.bindings[identity]
        except KeyError as exc:
            raise ContractError(f'{identity}: unknown binding') from exc

    def trigger(self, binding_id, trigger_id):
        trigger_id = definition_id(trigger_id)
        for trigger in self.binding(binding_id).triggers:
            if trigger.id == trigger_id:
                return trigger
        raise ContractError(f'{binding_id}: unknown trigger {trigger_id}')

    def handler(self, binding_id, trigger_id):
        from myworkflow.contracts.handlers import HandlerContract
        binding = self.binding(binding_id)
        return HandlerContract(binding, self.plans[binding.pipeline_id], self.trigger(binding.id, trigger_id))

    def payload(self, binding_id, trigger_id, values):
        """Map context keys to an ingress payload using the declared trigger."""
        from dataclasses import asdict, is_dataclass
        values = asdict(values) if is_dataclass(values) else values
        trigger = self.trigger(binding_id, trigger_id)
        return {source: values[self.artifacts[artifact].key] for artifact, source in trigger.input_mapping}

    def next_binding(self, binding_id, target_binding_id):
        target_binding_id = definition_id(target_binding_id)
        workflow_id = self.binding(binding_id).next_workflow_id
        workflow = next((w for w in self.model.workflows if w.id == workflow_id), None)
        if workflow is None or target_binding_id not in {b.id for b in workflow.bindings}:
            raise ContractError(f'{binding_id}: invalid next binding {target_binding_id}')
        return self.binding(target_binding_id)

    def values(self, ids, values, where):
        declarations = {self.artifacts[i].key: self.artifacts[i] for i in ids}
        if set(values) != set(declarations):
            raise ContractError(f"{where}: expected fields {sorted(declarations)}, got {sorted(values)}")
        normalized = {}
        for key, artifact in declarations.items():
            value = artifact.value_object.normalize(values[key]) if artifact.value_object else values[key]
            typ = TYPES[artifact.type]
            if type(value) is not typ:
                raise ContractError(f"{where}: {key} must be {typ.__name__}")
            normalized[key] = value
        return normalized

    def check(self, registry):
        for identity in sorted(self.implementation_ids):
            if identity not in registry.handlers:
                raise ContractError(f'{identity}: missing implementation')
