"""Deterministic business documentation."""
from myworkflow._internal.markdown import escape
from myworkflow.contracts.models import ContractCatalog, Lock

def render(catalog: ContractCatalog) -> str:
    """Generate deterministic Markdown; order is explicit declaration order."""
    catalog.validate()
    artifacts = {a.id: a.name for a in catalog.artifacts}
    pipelines = {p.id: p for p in catalog.pipelines}
    workflows = {w.id: w.name for w in catalog.workflows}
    lines = ["# 業務要件", ""]

    def names(ids):
        return "、".join(artifacts[i] for i in ids)

    cell = escape

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
            triggers = b.triggers
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
                    rows.append((s.name, f"排他キー：{names(s.keys)}。" + (f"名前空間：{s.namespace}。" if s.namespace != "business" else "") + f"範囲：{s.scope}。競合時：{s.conflict}。" + (f"最大待機：{s.timeout}秒。" if s.timeout else ""), "—", f"参照：{names(s.keys)}／保持：排他キー・ロック", identity + "/" + s.id))
                else:
                    uses = "／".join(f"{u.operation}：{artifacts[u.artifact_id]}" for u in s.uses) or "—"
                    rows.append((s.name, describe_step(s, artifacts), "—", uses, identity + "/" + s.id))
            ending = "終了コードとメッセージを返す。" if p.reply else "処理を完了する。応答は返さない。"
            if b.next_workflow_id:
                ending += f"次ワークフロー起動：{workflows[b.next_workflow_id]}。"
            rows.append(("結果返却" if p.reply else "完了", ending, "出力：" + ("終了コード・メッセージ" if p.reply else "なし（応答不要）"), ("保持：" + names(p.outputs)) if p.outputs else "—", identity + "/response"))
            for si, (name, overview, io, uses, fixed_id) in enumerate(rows, 1):
                number = f"{wi:03}-{bi:05}-{si:05}"
                slot = p.steps[si - 1].actor if si <= len(p.steps) else "system"
                actor = roles[dict(b.role_mapping)[slot]]
                values = (number, "—", actor, name, overview, io, uses, fixed_id)
                lines.append("| " + " | ".join(map(cell, values)) + " |")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def document_program(program, registry=None, *, details_link=None, data_definitions_link="data-definitions.md"):
    text = render(program.model) + "\n## 型付き契約\n\n| 固定ID | 名前 | コード上のキー | Python型 |\n| --- | --- | --- | --- |\n"
    safe = escape
    for a in program.artifacts.values():
        text += "| " + " | ".join(map(safe, (a.id, a.name, a.key, a.value_object.model.__name__ if a.value_object else a.type))) + " |\n"
    if program.model.value_objects:
        text += f"\n## データ定義への参照\n\n詳細な制約は別ファイルの[データ定義]({data_definitions_link})を参照。\n\n| アーティファクト固定ID | データ定義固定ID |\n| --- | --- |\n"
        for artifact in program.model.artifacts:
            if artifact.value_object:
                text += f"| {safe(artifact.id)} | [{safe(artifact.value_object.id)}]({data_definitions_link}#{artifact.value_object.id}) |\n"
    text += "\n## 起動定義の対応\n\n| トリガー固定ID | 配置 | パイプライン | 許可ロール |\n| --- | --- | --- | --- |\n"
    for b in program.bindings.values():
        for t in b.triggers:
            text += "| " + ' | '.join(map(safe, (t.id, b.id, b.pipeline_id, t.actor_role_id))) + " |\n"
    if registry:
        program.check(registry)
        text += "\n## 実装対応\n\n| 固定ID | 実装 |\n| --- | --- |\n"
        for identity in sorted(program.implementation_ids):
            fn = registry.handlers[identity]
            text += f"| {safe(identity)} | {safe(fn.__module__)}.{safe(fn.__name__)} |\n"
        text += "\nロックはEngine → LockProvider、受付認可はEngine → Principal.rolesで実行。"
        text += f"詳細は[実行設計]({details_link})を参照。\n" if details_link else "\n"
    return text


def describe_step(step, artifacts):
    text = step.summary
    if step.when:
        artifact, value = step.when
        text += f" 条件：{artifacts[artifact]}が{value}の場合。その他はスキップし次へ合流。"
    if step.compensate:
        text += f" 失敗時の補償：{step.compensate}（逆順、失敗した処理も対象）。"
    if step.attempts > 1:
        text += f" 一時障害のみ最大{step.attempts}回試行。"
    return text
