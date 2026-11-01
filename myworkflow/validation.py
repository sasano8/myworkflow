"""Structural and semantic contract checks."""
from myworkflow.models import Lock, Trigger


def validate_catalog(catalog):
    entities = [*catalog.artifacts, *catalog.pipelines, *catalog.workflows, *catalog.roles]
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

import keyword
import re
from myworkflow.errors import ContractError
from myworkflow.codegen import class_name

TYPES = {"str": str, "int": int, "bool": bool, "float": float}


def validate_names(program):
    catalog = program.model
    entities = [*catalog.artifacts, *catalog.pipelines, *catalog.workflows, *catalog.roles]
    entities += [s for p in catalog.pipelines for s in p.steps]
    entities += [b for w in catalog.workflows for b in w.bindings]
    entities += [t for w in catalog.workflows for b in w.bindings for t in b.triggers]
    ids = [e.id for e in entities]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", i) for i in ids):
        raise ContractError("IDs must be unique, nonempty and contain no slash")
    keys = [a["key"] for a in program.artifacts.values()]
    if len(keys) != len(set(keys)) or any(not k.isidentifier() or keyword.iskeyword(k) for k in keys):
        raise ContractError("Artifact keys must be unique Python identifiers")
    names = [class_name(p) for p in program.plans]
    if len(names) != len(set(names)) or any(not n.isidentifier() for n in names):
        raise ContractError("Pipeline IDs produce colliding or invalid interface names")
    for a in program.artifacts.values():
        if a["type"] not in TYPES:
            raise ContractError(f"{a['id']}: unsupported type")
    handler_ids = [s['id'] for s in program.steps.values() if s['kind'] != 'lock']
    compensation_ids = {s['compensate'] for s in program.steps.values() if s.get('compensate')}
    if compensation_ids & set(ids) or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", i) for i in compensation_ids):
        raise ContractError("Compensation IDs must be valid and distinct from entity IDs")
    function_names = [class_name(i).lower() for i in handler_ids + sorted(compensation_ids)]
    if len(function_names) != len(set(function_names)):
        raise ContractError("Implementation IDs produce colliding skeleton function names")


def validate_flow(program):
    for p in program.plans.values():
        if type(p.reply) is not bool:
            raise ContractError(f"{p.id}: reply must be boolean")
        available = set(p["inputs"])
        conditional = {}
        tested_conditions = set()
        for s in p["steps"]:
            if s["kind"] not in {"action", "lock"}:
                raise ContractError(f"{s['id']}: unknown step kind")
            condition = s.get("when")
            if condition:
                a, value = condition
                if a not in program.artifacts or a not in available or program.artifacts[a]["type"] != "bool" or type(value) is not bool:
                    raise ContractError(f"{s['id']}: branch needs an available boolean")
            if condition:
                tested_conditions.add(condition[0])
            if set(s.get('writes', ())) & tested_conditions:
                raise ContractError(f"{s['id']}: a tested branch condition cannot be reassigned")
            reads = set(s.get("reads", []))
            possible = available | conditional.get(tuple(condition or ()), set())
            if reads - possible:
                raise ContractError(f"{s['id']}: artifacts not available: {sorted(reads - possible)}")
            references = reads | set(s.get("writes", []))
            references |= {u[0] for u in s.get("uses", [])}
            if references - program.artifacts.keys():
                raise ContractError(f"{s['id']}: unknown artifact")
            if type(s.get("attempts", 1)) is not int or s.get("attempts", 1) < 1:
                raise ContractError(f"{s['id']}: attempts must be a positive integer")
            if s["kind"] == "lock":
                import math
                if not isinstance(s.namespace, str) or not s.namespace or type(s.timeout) not in (int, float) or not math.isfinite(s.timeout) or s.timeout < 0:
                    raise ContractError(f"{s['id']}: invalid lock namespace or timeout")
                if not reads or condition or s.get("writes"):
                    raise ContractError(f"{s['id']}: lock requires unconditional keys, no writes")
            target = conditional.setdefault(tuple(condition), set()) if condition else available
            target.update(s.get("writes", []))
            if condition:
                a, _ = condition
                available.update(conditional.get((a, True), set()) & conditional.get((a, False), set()))
        if set(p["inputs"] + p["outputs"]) - program.artifacts.keys() or set(p["outputs"]) - available:
            raise ContractError(f"{p['id']}: outputs must be available on every path")


def validate_bindings(program):
    for b in program.bindings.values():
        if b["pipeline"] not in program.plans:
            raise ContractError(f"{b['id']}: unknown pipeline")
        if not b["triggers"]:
            raise ContractError(f"{b['id']}: no triggers")
        if b.get('next_workflow') is not None and b['next_workflow'] not in {w.id for w in program.model.workflows}:
            raise ContractError(f"{b['id']}: unknown next workflow")
        for t in b["triggers"]:
            mapping = t["mapping"]
            if set(mapping) != set(program.plans[b["pipeline"]]["inputs"]):
                raise ContractError(f"{t['id']}: mapping does not match input contract")
            if len(set(mapping.values())) != len(mapping) or any(not v for v in mapping.values()):
                raise ContractError(f"{t['id']}: input sources must be nonempty and unambiguous")
    program.catalog().validate()



def validate_program(program):
    validate_names(program)
    validate_flow(program)
    validate_bindings(program)
