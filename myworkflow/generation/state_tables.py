"""State transition tables from validated declarations."""

from myworkflow.contracts.state_graph import StateGraph
from myworkflow.contracts.models import ContractCatalog
from myworkflow._internal.markdown import escape


def render_state_graph(graph: StateGraph, catalog: ContractCatalog) -> str:
    """Render declarations, not a runtime state/history report."""
    graph.validate(catalog)
    roles = {r.id: r.display_name for r in catalog.roles}
    pipelines = {p.id: p.name for p in catalog.pipelines}
    lines = [
        "# 状態遷移",
        "",
        "| 連番 | ワークフロー | トランジション | 実行者 | トリガー | 現在の状態 | 成功後の状態 | 条件 | パイプライン | 固定ID |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for number, t in enumerate(graph.transitions, 1):
        cells = (
            f"{number:03}",
            graph.workflow.name,
            t.name,
            roles[t.trigger.actor_role_id],
            t.trigger.name,
            t.source.name,
            t.target.name,
            t.condition or "—",
            pipelines[t.binding.pipeline_id],
            f"{graph.workflow.id}/{t.id}",
        )
        lines.append("| " + " | ".join(escape(c) for c in cells) + " |")
    return "\n".join(lines) + "\n"
