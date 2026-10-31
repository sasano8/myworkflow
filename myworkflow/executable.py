"""Small synchronous contract executor. Durable orchestration belongs to Temporal."""
from __future__ import annotations

from collections.abc import MutableMapping
from contextlib import ExitStack
from dataclasses import asdict, dataclass, is_dataclass
import inspect
import keyword
import re
from typing import get_type_hints

from myworkflow import Artifact, Binding, Catalog, Lock, Pipeline, Role, Step, Trigger, Use, Workflow, render

TYPES = {"str": str, "int": int, "bool": bool, "float": float}


class ContractError(ValueError):
    pass


class RetryableError(Exception):
    pass


class ExecutionFailed(Exception):
    def __init__(self, step_id, cause, compensation_errors):
        self.step_id = step_id
        self.cause = cause
        self.compensation_errors = compensation_errors
        super().__init__(f"{step_id}: {cause}; compensation failures: {compensation_errors}")


@dataclass
class Context:
    values: dict
    services: object
    run_id: str
    actor: str
    events: list


class Registry:
    def __init__(self):
        self.handlers = {}

    def implements(self, step_id):
        def register(fn):
            if step_id in self.handlers:
                raise ContractError(f"{step_id}: duplicate implementation")
            hints = get_type_hints(fn)
            if list(inspect.signature(fn).parameters) != ["ctx"] or hints != {"ctx": Context, "return": type(None)}:
                raise ContractError(f"{step_id}: expected (ctx: Context) -> None")
            self.handlers[step_id] = fn
            return fn
        return register


class Program:
    def __init__(self, spec):
        self.spec = spec
        self.artifacts = {a["id"]: a for a in spec["artifacts"]}
        self.plans = {p["id"]: p for p in spec["pipelines"]}
        self.bindings = {b["id"]: b for w in spec["workflows"] for b in w["bindings"]}
        self.steps = {s["id"]: s for p in spec["pipelines"] for s in p["steps"]}
        self.validate()

    def validate(self):
        ids = [e["id"] for section in ("artifacts", "pipelines", "workflows", "roles") for e in self.spec[section]]
        ids += [s["id"] for p in self.plans.values() for s in p["steps"]]
        ids += [b["id"] for w in self.spec["workflows"] for b in w["bindings"]]
        ids += [t["id"] for b in self.bindings.values() for t in b["triggers"]]
        if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", i) for i in ids):
            raise ContractError("IDs must be unique, nonempty and contain no slash")
        keys = [a["key"] for a in self.artifacts.values()]
        if len(keys) != len(set(keys)) or any(not k.isidentifier() or keyword.iskeyword(k) for k in keys):
            raise ContractError("Artifact keys must be unique Python identifiers")
        names = [class_name(p) for p in self.plans]
        if len(names) != len(set(names)) or any(not n.isidentifier() for n in names):
            raise ContractError("Pipeline IDs produce colliding or invalid interface names")
        for a in self.artifacts.values():
            if a["type"] not in TYPES:
                raise ContractError(f"{a['id']}: unsupported type")
        handler_ids = [s['id'] for s in self.steps.values() if s['kind'] != 'lock']
        compensation_ids = {s['compensate'] for s in self.steps.values() if s.get('compensate')}
        if compensation_ids & set(ids) or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", i) for i in compensation_ids):
            raise ContractError("Compensation IDs must be valid and distinct from entity IDs")
        function_names = [class_name(i).lower() for i in handler_ids + sorted(compensation_ids)]
        if len(function_names) != len(set(function_names)):
            raise ContractError("Implementation IDs produce colliding skeleton function names")
        for p in self.plans.values():
            if not p["reply"] and p["outputs"]:
                raise ContractError(f"{p['id']}: no-reply pipeline has outputs")
            available = set(p["inputs"])
            conditional = {}
            for s in p["steps"]:
                if s["kind"] not in {"action", "lock"}:
                    raise ContractError(f"{s['id']}: unknown step kind")
                condition = s.get("when")
                if condition:
                    a, value = condition
                    if a not in self.artifacts or a not in available or self.artifacts[a]["type"] != "bool" or type(value) is not bool:
                        raise ContractError(f"{s['id']}: branch needs an available boolean")
                reads = set(s.get("reads", []))
                possible = available | conditional.get(tuple(condition or ()), set())
                if reads - possible:
                    raise ContractError(f"{s['id']}: artifacts not available: {sorted(reads - possible)}")
                references = reads | set(s.get("writes", []))
                references |= {u[0] for u in s.get("uses", [])}
                if references - self.artifacts.keys():
                    raise ContractError(f"{s['id']}: unknown artifact")
                if type(s.get("attempts", 1)) is not int or s.get("attempts", 1) < 1:
                    raise ContractError(f"{s['id']}: attempts must be a positive integer")
                if s["kind"] == "lock":
                    if not reads or condition or s.get("writes"):
                        raise ContractError(f"{s['id']}: lock requires unconditional keys, no writes")
                target = conditional.setdefault(tuple(condition), set()) if condition else available
                target.update(s.get("writes", []))
                if condition:
                    a, _ = condition
                    available.update(conditional.get((a, True), set()) & conditional.get((a, False), set()))
            if set(p["inputs"] + p["outputs"]) - self.artifacts.keys() or set(p["outputs"]) - available:
                raise ContractError(f"{p['id']}: outputs must be available on every path")
        for b in self.bindings.values():
            if b["pipeline"] not in self.plans:
                raise ContractError(f"{b['id']}: unknown pipeline")
            if not b["triggers"]:
                raise ContractError(f"{b['id']}: no triggers")
            if b.get('next_workflow') is not None and b['next_workflow'] not in {w['id'] for w in self.spec['workflows']}:
                raise ContractError(f"{b['id']}: unknown next workflow")
            for t in b["triggers"]:
                mapping = t["mapping"]
                if set(mapping) != set(self.plans[b["pipeline"]]["inputs"]):
                    raise ContractError(f"{t['id']}: mapping does not match input contract")
                if len(set(mapping.values())) != len(mapping) or any(not v for v in mapping.values()):
                    raise ContractError(f"{t['id']}: input sources must be nonempty and unambiguous")
        self.catalog().validate()

    def catalog(self):
        def step(s):
            if s["kind"] == "lock":
                return Lock(s["id"], s["name"], tuple(s["reads"]))
            text = s["summary"]
            if s.get("when"):
                a, value = s["when"]
                text += f" 条件：{self.artifacts[a]['name']}が{value}の場合。その他はスキップし次へ合流。"
            if s.get("compensate"):
                text += f" 失敗時の補償：{s['compensate']}（逆順、失敗した処理も対象）。"
            if s.get("attempts", 1) > 1:
                text += f" 一時障害のみ最大{s['attempts']}回試行。"
            return Step(s["id"], s["name"], text, tuple(Use(a, op) for a, op in s.get("uses", [])))

        def binding(b):
            def trigger(t):
                return Trigger(t["id"], t["name"], tuple(t["mapping"].items()), wait=t.get("wait"), actor_role_id=t["role"])
            t = b["triggers"][0]
            return Binding(b["id"], b["pipeline"], t["name"], tuple(t["mapping"].items()),
                           wait=t.get("wait"), next_workflow_id=b.get("next_workflow"),
                           additional_triggers=tuple(trigger(t) for t in b["triggers"][1:]),
                           actor_role_id=t["role"], role_mapping=(("system", "role.system"),))
        return Catalog(
            tuple(Artifact(a["id"], a["name"]) for a in self.artifacts.values()),
            tuple(Pipeline(p["id"], p["name"], tuple(p["inputs"]), tuple(p["outputs"]), tuple(map(step, p["steps"])), p["reply"]) for p in self.plans.values()),
            tuple(Workflow(w["id"], w["name"], tuple(map(binding, w["bindings"]))) for w in self.spec["workflows"]),
            tuple(Role(r["id"], r["name"], r["display_name"]) for r in self.spec["roles"]),
        )

    def values(self, ids, values, where):
        expected = {self.artifacts[i]["key"]: TYPES[self.artifacts[i]["type"]] for i in ids}
        if set(values) != set(expected):
            raise ContractError(f"{where}: expected fields {sorted(expected)}, got {sorted(values)}")
        for key, typ in expected.items():
            if type(values[key]) is not typ:
                raise ContractError(f"{where}: {key} must be {typ.__name__}")

    def check(self, registry):
        for s in self.steps.values():
            if s["kind"] != "lock":
                for identity in [s["id"], *([s["compensate"]] if s.get("compensate") else [])]:
                    if identity not in registry.handlers:
                        raise ContractError(f"{identity}: missing implementation")

    def documentation(self, registry=None, *, details_link="../../docs/execution-design.md"):
        text = render(self.catalog()) + "\n## 型付き契約\n\n| 固定ID | 名前 | コード上のキー | Python型 |\n| --- | --- | --- | --- |\n"
        def safe(v):
            return str(v).replace('&', '&amp;').replace('<', '&lt;').replace('|', '&#124;').replace('\n', '<br>')
        for a in self.artifacts.values():
            text += "| " + " | ".join(safe(a[k]) for k in ("id", "name", "key", "type")) + " |\n"
        text += "\n## 起動定義の対応\n\n| トリガー固定ID | 配置 | パイプライン | 許可ロール |\n| --- | --- | --- | --- |\n"
        for b in self.bindings.values():
            for t in b['triggers']:
                text += "| " + " | ".join(map(safe, (t['id'], b['id'], b['pipeline'], t['role']))) + " |\n"
        if registry:
            self.check(registry)
            text += "\n## 実装対応\n\n| 固定ID | 実装 |\n| --- | --- |\n"
            for identity in sorted({s['id'] for s in self.steps.values() if s['kind'] != 'lock'} | {s['compensate'] for s in self.steps.values() if s.get('compensate')}):
                fn = registry.handlers[identity]
                text += f"| {safe(identity)} | {safe(fn.__module__)}.{safe(fn.__name__)} |\n"
            text += f"\nロックはEngine → services.lock、受付認可はEngine → Principal.rolesで実行。詳細は[実行設計]({details_link})を参照。\n"
        return text


@dataclass(frozen=True)
class Principal:
    id: str
    roles: frozenset[str]


class Engine:
    def __init__(self, program, registry, services, interfaces=None):
        program.check(registry)
        self.program, self.registry, self.services = program, registry, services
        self.interfaces = interfaces
        if interfaces:
            for p in program.plans.values():
                for direction, ids in (("Request", p["inputs"]), ("Response", p["outputs"])):
                    name = class_name(p["id"]) + direction
                    cls = getattr(interfaces, name, None)
                    expected = {program.artifacts[i]["key"]: TYPES[program.artifacts[i]["type"]] for i in ids}
                    if cls is None or not is_dataclass(cls) or get_type_hints(cls) != expected:
                        raise ContractError(f"{p['id']}: stale or invalid {direction} interface")

    def invoke(self, binding_id, trigger_id, payload, principal, *, run_id):
        b = self.program.bindings[binding_id]
        t = next((t for t in b["triggers"] if t["id"] == trigger_id), None)
        if t is None:
            raise ContractError(f"{binding_id}: unknown trigger {trigger_id}")
        if t["role"] not in principal.roles:
            raise PermissionError(f"{trigger_id}: {principal.id} lacks {t['role']}")
        if set(payload) != set(t["mapping"].values()):
            raise ContractError(f"{trigger_id}: payload fields do not match mapping")
        values = {self.program.artifacts[a]["key"]: payload[source] for a, source in t["mapping"].items()}
        return self.run(b["pipeline"], values, actor=principal.id, run_id=run_id)

    def run(self, pipeline_id, request, *, actor, run_id):
        p = self.program.plans[pipeline_id]
        values = asdict(request) if is_dataclass(request) else dict(request)
        self.program.values(p["inputs"], values, pipeline_id)
        ctx = Context(values, self.services, run_id, actor, [])
        self.services.begin(run_id)
        compensations = []
        with ExitStack() as stack:
            try:
                for s in p["steps"]:
                    condition = s.get("when")
                    if condition and values[self.program.artifacts[condition[0]]["key"]] != condition[1]:
                        ctx.events.append((s["id"], "skipped"))
                        continue
                    if s["kind"] == "lock":
                        keys = tuple((a, values[self.program.artifacts[a]["key"]]) for a in s["reads"])
                        stack.enter_context(self.services.lock(keys))
                        ctx.events.append((s["id"], "locked"))
                        continue
                    if s.get("compensate"):
                        # Register before executing: remote success with a lost response is ambiguous.
                        compensations.append((s["id"], s["compensate"]))
                    for attempt in range(s.get("attempts", 1)):
                        try:
                            self._call(s["id"], ctx, s["reads"], s["writes"])
                            ctx.events.append((s["id"], "completed"))
                            break
                        except RetryableError:
                            if attempt + 1 == s.get("attempts", 1):
                                raise
                            ctx.events.append((s["id"], "retry"))
                result = {self.program.artifacts[a]["key"]: values[self.program.artifacts[a]["key"]] for a in p["outputs"]}
                self.program.values(p["outputs"], result, pipeline_id)
                self.services.record(run_id, ctx.events, "completed")
                if self.interfaces and p["reply"]:
                    return getattr(self.interfaces, class_name(pipeline_id) + "Response")(**result)
                return result if p["reply"] else None
            except Exception as exc:
                ctx.events.append((s["id"] if 's' in locals() else pipeline_id, "failed"))
                errors = []
                for original, identity in reversed(compensations):
                    ctx.events.append((identity, "compensating"))
                    try:
                        self.registry.handlers[identity](ctx)
                        ctx.events.append((identity, "compensated"))
                    except Exception as compensation_error:
                        errors.append((identity, str(compensation_error)))
                        ctx.events.append((identity, "compensation-failed"))
                status = "manual-recovery" if errors else "failed"
                self.services.record(run_id, ctx.events, status)
                raise ExecutionFailed(s["id"] if 's' in locals() else pipeline_id, exc, errors) from exc

    def _call(self, identity, ctx, reads, writes):
        keys = {self.program.artifacts[a]["key"] for a in reads}
        selected = {k: ctx.values[k] for k in keys if k in ctx.values}
        self.program.values(reads, selected, identity)
        before = dict(ctx.values)
        allowed = {self.program.artifacts[a]["key"] for a in writes}
        raw = ctx.values
        ctx.values = StepValues(raw, keys, allowed, identity)
        try:
            if self.registry.handlers[identity](ctx) is not None:
                raise ContractError(f"{identity}: handler must return None")
        finally:
            ctx.values = raw
        changed = {k for k in before.keys() | ctx.values.keys() if k not in before or k not in ctx.values or before[k] != ctx.values[k]}
        if changed - allowed:
            raise ContractError(f"{identity}: undeclared context writes {sorted(changed - allowed)}")
        self.program.values(writes, {k: ctx.values[k] for k in allowed if k in ctx.values}, identity)


class StepValues(MutableMapping):
    def __init__(self, values, reads, writes, identity):
        self.values, self.reads, self.writes, self.identity = values, reads, writes, identity

    def __getitem__(self, key):
        if key not in self.reads and key not in self.writes:
            raise ContractError(f"{self.identity}: undeclared context read {key}")
        return self.values[key]

    def __setitem__(self, key, value):
        if key not in self.writes:
            raise ContractError(f"{self.identity}: undeclared context write {key}")
        self.values[key] = value

    def __delitem__(self, key):
        raise ContractError(f"{self.identity}: context deletion is not supported")

    def __iter__(self):
        return iter(k for k in self.values if k in self.reads or k in self.writes)

    def __len__(self):
        return sum(1 for _ in self)


def class_name(identity):
    return ''.join(part.title() for part in identity.replace('.', '-').split('-'))


def interfaces_source(program):
    lines = ['"""Generated interfaces. Edit the contract, then regenerate."""', 'from dataclasses import dataclass', '']
    for p in program.plans.values():
        for direction, ids in (("Request", p["inputs"]), ("Response", p["outputs"])):
            lines.extend(['@dataclass(frozen=True)', f'class {class_name(p["id"])}{direction}:'])
            lines.extend([f'    {program.artifacts[a]["key"]}: {program.artifacts[a]["type"]}' for a in ids] or ['    pass'])
            lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def skeleton_source(program):
    lines = ['"""Generated skeleton: copy into your implementation; never overwrite existing work."""',
             'from myworkflow.executable import Context, Registry', '', 'registry = Registry()', '']
    ids = {s['id'] for s in program.steps.values() if s['kind'] != 'lock'} | {s['compensate'] for s in program.steps.values() if s.get('compensate')}
    for identity in sorted(ids):
        lines.extend([f'@registry.implements({identity!r})', f'def {class_name(identity).lower()}(ctx: Context) -> None:',
                      f'    raise NotImplementedError({identity!r})', ''])
    return '\n'.join(lines).rstrip() + '\n'
