"""Compiler checks for names, dataflow and bindings."""

import keyword
import re
from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.names import class_name
from myworkflow.contracts.models import Lock

from myworkflow.contracts.value_objects import PRIMITIVES as TYPES


def validate_names(program):
    keys = [a.key for a in program.artifacts.values()]
    if len(keys) != len(set(keys)) or any(not k.isidentifier() or keyword.iskeyword(k) for k in keys):
        raise ContractError("Artifact keys must be unique Python identifiers")
    names = [class_name(p) for p in program.plans]
    if len(names) != len(set(names)) or any(not n.isidentifier() for n in names):
        raise ContractError("Pipeline IDs produce colliding or invalid interface names")
    for a in program.artifacts.values():
        if a.type not in TYPES:
            raise ContractError(f'{a.id}: unsupported type')
        if a.value_object is not None:
            a.value_object.check()
            schema_type = a.value_object.model.model_json_schema().get('type')
            expected = {'str': 'string', 'int': 'integer', 'bool': 'boolean', 'float': 'number', 'dict': 'object'}[a.type]
            if schema_type != expected:
                raise ContractError(f'{a.id}: value object JSON type must match {a.type}')
    handler_ids = [s.id for s in program.processing_steps]
    compensation_ids = {s.compensate for s in program.processing_steps if s.compensate}
    if compensation_ids & {e.id for e in program.model.entities} or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", i) for i in compensation_ids):
        raise ContractError("Compensation IDs must be valid and distinct from entity IDs")
    function_names = [class_name(i).lower() for i in handler_ids + sorted(compensation_ids)]
    if len(function_names) != len(set(function_names)):
        raise ContractError("Implementation IDs produce colliding skeleton function names")


def validate_flow(program):
    for p in program.plans.values():
        available = set(p.inputs)
        conditional = {}
        tested_conditions = set()
        for s in p.steps:
            if s.kind not in {"action", "lock"}:
                raise ContractError(f'{s.id}: unknown step kind')
            condition = None if isinstance(s, Lock) else s.when
            if condition:
                a, value = condition
                if a not in program.artifacts or a not in available or program.artifacts[a].type != "bool" or type(value) is not bool:
                    raise ContractError(f'{s.id}: branch needs an available boolean')
                tested_conditions.add(condition[0])
            if set(s.writes) & tested_conditions:
                raise ContractError(f'{s.id}: a tested branch condition cannot be reassigned')
            reads = set(s.reads)
            possible = available | conditional.get(tuple(condition or ()), set())
            if reads - possible:
                raise ContractError(f'{s.id}: artifacts not available: {sorted(reads - possible)}')
            references = reads | set(s.writes)
            references |= {u.artifact_id for u in s.uses}
            if references - program.artifacts.keys():
                raise ContractError(f'{s.id}: unknown artifact')
            if not isinstance(s, Lock) and (type(s.attempts) is not int or s.attempts < 1):
                raise ContractError(f'{s.id}: attempts must be a positive integer')
            if s.kind == "lock":
                import math
                if not isinstance(s.namespace, str) or not s.namespace or type(s.timeout) not in (int, float) or not math.isfinite(s.timeout) or s.timeout < 0:
                    raise ContractError(f'{s.id}: invalid lock namespace or timeout')
                if any(program.artifacts[a].type == 'dict' for a in reads):
                    raise ContractError(f'{s.id}: lock keys require scalar artifacts')
                if not reads or condition or s.writes:
                    raise ContractError(f'{s.id}: lock requires unconditional keys, no writes')
            target = conditional.setdefault(tuple(condition), set()) if condition else available
            target.update(s.writes)
            if condition:
                a, _ = condition
                available.update(conditional.get((a, True), set()) & conditional.get((a, False), set()))
        if set(p.inputs + p.outputs) - program.artifacts.keys() or set(p.outputs) - available:
            raise ContractError(f'{p.id}: outputs must be available on every path')


def validate_program(program):
    program.model.validate()
    validate_names(program)
    validate_flow(program)
