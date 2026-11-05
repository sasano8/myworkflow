"""Shared annotation protocol and opaque, namespaced extension attributes."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import math
from typing import Protocol, TypeVar

from myworkflow.contracts.errors import ContractError


class Annotated(Protocol):
    __myworkflow__: object


def declaration(value):
    """Read attached metadata without calling a function or evaluating a descriptor."""
    try:
        return vars(value).get('__myworkflow__', value)
    except TypeError:
        return value


F = TypeVar('F', bound=Callable)


def annotate(spec: object) -> Callable[[F], F]:
    """Attach a declaration; leave signatures, identity and execution unchanged."""
    spec = declaration(spec)
    if not isinstance(getattr(spec, 'id', None), str) or not spec.id:
        raise ContractError('Annotation requires a declaration with a nonempty string ID')
    def decorate(target: F) -> F:
        if not callable(target) or not hasattr(target, '__dict__'):
            raise ContractError('Annotations require a function, class or callable with attributes')
        if '__myworkflow__' in vars(target):
            raise ContractError(f'{spec.id}: already annotated')
        target.__myworkflow__ = spec
        return target
    return decorate


class _FrozenDict(dict):
    """A read-only dict that still works with dataclasses.asdict and JSON tools."""
    def _readonly(self, *args, **kwargs):
        raise TypeError('Extension mappings are read-only')

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _readonly


def _freeze(value, active=frozenset()):
    if isinstance(value, (Mapping, list, tuple)):
        if id(value) in active:
            raise ContractError('Extension containers must be acyclic')
        active = active | {id(value)}
        if isinstance(value, Mapping):
            if any(not isinstance(k, str) for k in value):
                raise ContractError('Extension keys must be strings')
            return _FrozenDict({k: _freeze(v, active) for k, v in value.items()})
        return tuple(_freeze(v, active) for v in value)
    return value


@dataclass(frozen=True)
class Extensible:
    extensions: Mapping[str, object] = field(default_factory=dict, kw_only=True, hash=False)

    def __post_init__(self):
        if not isinstance(self.extensions, Mapping):
            raise ContractError('extensions must be a mapping')
        object.__setattr__(self, 'extensions', _freeze(self.extensions))


def extension_fields(value, encoder=None):
    """JSON boundary only; arbitrary Python values stay intact until exported."""
    def encode(item, active=frozenset()):
        if id(item) in active:
            raise ContractError('Extension encoding must be acyclic')
        active = active | {id(item)}
        if isinstance(item, Mapping):
            if any(not isinstance(k, str) for k in item):
                raise ContractError('Extension JSON keys must be strings')
            return {k: encode(v, active) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [encode(v, active) for v in item]
        if type(item) in (str, int, bool, type(None)) or type(item) is float and math.isfinite(item):
            return item
        if encoder is not None:
            converted = encoder(item)
            if converted is not item:
                return encode(converted, active)
        raise ContractError(f'Unsupported extension value {type(item).__name__}; supply an extension_encoder')
    return {'extensions': encode(value.extensions)} if value.extensions else {}
