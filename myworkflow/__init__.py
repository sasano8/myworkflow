"""Business contracts. Declarations describe behavior; they do not execute it."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    id: str
    name: str  # formal business name
    display_name: str


@dataclass(frozen=True)
class Artifact:
    id: str
    name: str


@dataclass(frozen=True)
class Use:
    artifact_id: str
    operation: str  # 参照、保持、DB読取、DB作成、DB更新、送信


@dataclass(frozen=True)
class Step:
    id: str
    name: str
    summary: str
    uses: tuple[Use, ...] = ()
    actor: str = "system"  # abstract role slot, resolved by Binding


@dataclass(frozen=True)
class Lock:
    id: str
    name: str
    keys: tuple[str, ...]  # artifact IDs already in context
    conflict: str = "拒否"
    scope: str = "パイプライン終了まで（異常終了を含む）"
    actor: str = "system"


@dataclass(frozen=True)
class Pipeline:
    id: str
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    steps: tuple[Step | Lock, ...]
    reply: bool = True


@dataclass(frozen=True)
class Trigger:
    id: str
    name: str
    input_mapping: tuple[tuple[str, str], ...]
    after: str | None = None
    wait: str | None = None
    actor_role_id: str | None = None


@dataclass(frozen=True)
class Binding:
    id: str  # placement identity, independent of reusable pipeline identity
    pipeline_id: str
    trigger: str
    input_mapping: tuple[tuple[str, str], ...]  # contract input -> source description
    after: str | None = None  # preceding placement, if any
    wait: str | None = None
    next_workflow_id: str | None = None
    additional_triggers: tuple[Trigger, ...] = ()
    actor_role_id: str | None = None
    role_mapping: tuple[tuple[str, str], ...] = ()  # abstract slot -> concrete role ID


@dataclass(frozen=True)
class Workflow:
    id: str
    name: str
    bindings: tuple[Binding, ...]


@dataclass(frozen=True)
class Catalog:
    artifacts: tuple[Artifact, ...]
    pipelines: tuple[Pipeline, ...]
    workflows: tuple[Workflow, ...]
    roles: tuple[Role, ...] = ()

    def validate(self) -> None:
        entities = [*self.artifacts, *self.pipelines, *self.workflows, *self.roles]
        entities += [s for p in self.pipelines for s in p.steps]
        entities += [b for w in self.workflows for b in w.bindings]
        entities += [t for w in self.workflows for b in w.bindings for t in b.additional_triggers]
        ids = [e.id for e in entities]
        if any(not i.strip() for i in ids) or len(ids) != len(set(ids)):
            raise ValueError("IDs must be nonempty and globally unique")
        roles = {r.id for r in self.roles}
        if any(not r.name.strip() or not r.display_name.strip() for r in self.roles):
            raise ValueError("Role names must be nonempty")
        artifacts = {a.id for a in self.artifacts}
        pipelines = {p.id: p for p in self.pipelines}
        workflows = {w.id for w in self.workflows}
        for p in self.pipelines:
            if not p.reply and p.outputs:
                raise ValueError("A no-reply pipeline cannot declare response outputs")
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
        for w in self.workflows:
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


def render(catalog: Catalog) -> str:
    """Generate deterministic Markdown; order is explicit declaration order."""
    catalog.validate()
    artifacts = {a.id: a.name for a in catalog.artifacts}
    pipelines = {p.id: p for p in catalog.pipelines}
    workflows = {w.id: w.name for w in catalog.workflows}
    lines = ["# 業務要件", ""]

    def names(ids):
        return "、".join(artifacts[i] for i in ids)

    def cell(value):
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\r\n", "<br>").replace("\r", "<br>").replace("\n", "<br>")

    roles = {r.id: r.display_name for r in catalog.roles}
    lines.extend(["## ロール一覧", "", "| ロールID | 業務上の正式名 | 表示名 |", "| --- | --- | --- |"])
    for r in catalog.roles:
        lines.append("| " + " | ".join(map(cell, (r.id, r.name, r.display_name))) + " |")
    lines.append("")
    for wi, w in enumerate(catalog.workflows, 1):
        lines.extend([f"## {wi:03} {cell(w.name)}", ""])
        if not w.bindings:
            lines.extend(["起動定義なし（処理内容は未定義）。", ""])
        for bi, b in enumerate(w.bindings, 1):
            p = pipelines[b.pipeline_id]
            identity = f"{w.id}/{b.id}/{p.id}"
            lines.extend([f"### {wi:03}-{bi:05} {cell(p.name)}", "",
                          "| 連番 | トリガー | 実行者 | ステップ名 | 処理概要 | 入出力 | アーティファクト操作 | 固定ID |",
                          "| --- | --- | --- | --- | --- | --- | --- | --- |"])
            triggers = (Trigger(b.id, b.trigger, b.input_mapping, b.after, b.wait, b.actor_role_id), *b.additional_triggers)
            for ti, t in enumerate(triggers, 1):
                summary = ""
                if t.after:
                    summary += f"先行配置：{t.after}。"
                if t.wait:
                    summary += f"待機・再開条件：{t.wait}。"
                summary += "入力元：" + ("、".join(f"{artifacts[target]} ← {source}" for target, source in t.input_mapping) or "なし")
                fixed_id = identity + "/request" + (f"/{t.id}" if ti > 1 else "")
                values = (f"{wi:03}-{bi:05}-00000", f"トリガー{ti}：{t.name}", roles[t.actor_role_id], "受付", summary,
                          "入力：" + (names(p.inputs) or "なし"), "—", fixed_id)
                lines.append("| " + " | ".join(map(cell, values)) + " |")
            rows = []
            for s in p.steps:
                if isinstance(s, Lock):
                    rows.append((s.name, f"排他キー：{names(s.keys)}。範囲：{s.scope}。競合時：{s.conflict}。", "—", f"参照：{names(s.keys)}／保持：排他キー・ロック", identity + "/" + s.id))
                else:
                    uses = "／".join(f"{u.operation}：{artifacts[u.artifact_id]}" for u in s.uses) or "—"
                    rows.append((s.name, s.summary, "—", uses, identity + "/" + s.id))
            ending = "結果を返す。" if p.reply else "処理を完了する。応答は返さない。"
            if b.next_workflow_id:
                ending += f"次ワークフロー起動：{workflows[b.next_workflow_id]}。"
            rows.append(("結果返却" if p.reply else "完了", ending, "出力：" + ((names(p.outputs) or "なし") if p.reply else "なし（応答不要）"), "—", identity + "/response"))
            for si, (name, overview, io, uses, fixed_id) in enumerate(rows, 1):
                number = f"{wi:03}-{bi:05}-{si:05}"
                slot = p.steps[si - 1].actor if si <= len(p.steps) else "system"
                actor = roles[dict(b.role_mapping)[slot]]
                values = (number, "—", actor, name, overview, io, uses, fixed_id)
                lines.append("| " + " | ".join(map(cell, values)) + " |")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
