"""Explicit, validated implementation registration and test replacement."""
import inspect
from types import MappingProxyType
from typing import get_type_hints
from myworkflow.errors import ContractError
from myworkflow.runtime.context import Context


class Registry:
    def __init__(self):
        self._handlers = {}

    @property
    def handlers(self):
        return MappingProxyType(self._handlers)

    def _validate(self, identity, fn):
        try:
            hints = get_type_hints(fn)
        except (TypeError, NameError) as exc:
            raise ContractError(f'{identity}: invalid handler annotations') from exc
        if list(inspect.signature(fn).parameters) != ['ctx'] or hints != {'ctx': Context, 'return': type(None)}:
            raise ContractError(f'{identity}: expected (ctx: Context) -> None')

    def implements(self, identity):
        def register(fn):
            if identity in self._handlers:
                raise ContractError(f'{identity}: duplicate implementation')
            self._validate(identity, fn)
            self._handlers[identity] = fn
            return fn
        return register

    def replace(self, identity, fn):
        if identity not in self._handlers:
            raise ContractError(f'{identity}: missing implementation')
        self._validate(identity, fn)
        self._handlers[identity] = fn

    def remove(self, identity):
        del self._handlers[identity]

    def fork(self):
        result = Registry()
        result._handlers.update(self._handlers)
        return result
