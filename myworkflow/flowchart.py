"""Business flow diagrams from the same declarations as the state transition table."""
import string

from myworkflow.markdown import escape
from myworkflow.models import ContractCatalog
from myworkflow.state_graph import StateGraph


def _label(value: str) -> str:
    """Mermaid entities keep labels from becoming syntax, HTML or Markdown fences."""
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    return '<br/>'.join(''.join(f'#{ord(c)};' if c in string.punctuation else c for c in line)
                       for line in value.split('\n'))


def render_business_flow(graph: StateGraph, catalog: ContractCatalog, *, details: bool = False) -> str:
    """Generate Markdown with Mermaid; show declared success paths, not execution history.

    The compact view shows states, actions, actors and triggers. The detailed view
    adds pipeline names and condition descriptions, without evaluating any guards.
    Node aliases are generated internally, never interpolated from customer IDs.
    No outgoing edge does not imply successful completion; no final node is inferred.
    """
    graph.validate(catalog)
    roles = {r.id: r.display_name for r in catalog.roles}
    pipelines = {p.id: p.name for p in catalog.pipelines}
    states = {s.id: f'state_{number}' for number, s in enumerate(graph.states)}
    lines = ['# 業務フロー図', '', f'## {escape(graph.workflow.name)}', '', '```mermaid', 'flowchart TD',
             '    start(("開始"))']
    for state in graph.states:
        lines.append(f'    {states[state.id]}["{_label(state.name)}"]')
    lines.append(f'    start --> {states[graph.initial.id]}')
    for number, transition in enumerate(graph.transitions, 1):
        label = [f'{number:03} {transition.name}', f'実行者：{roles[transition.trigger.actor_role_id]}',
                 f'トリガー：{transition.trigger.name}']
        if details:
            label.append(f'パイプライン：{pipelines[transition.binding.pipeline_id]}')
            if transition.condition:
                label.append(f'条件：{transition.condition}')
        node = f'action_{number}'
        lines.append(f'    {node}["' + '<br/>'.join(_label(part) for part in label) + '"]')
        lines.append(f'    {states[transition.source.id]} --> {node}')
        lines.append(f'    {node} -->|成功| {states[transition.target.id]}')
    lines.extend(['```', '', '操作の番号は状態遷移表の連番に対応します。入出力・アーティファクト操作はパイプラインの詳細表を参照してください。'])
    if not details:
        lines.append('条件・対応パイプラインは状態遷移表に記載します。')
    lines.extend(['業務上の宣言を図示しており、実行履歴や状態更新の実装済み範囲を示す図ではありません。', ''])
    return '\n'.join(lines)
