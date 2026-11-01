"""generation behavior and invariants."""
from dataclasses import replace
import pytest
from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.state_graph import State
from myworkflow.generation.state_tables import render_state_graph
from tests._support.state_graph import example

def test_render_column_order_and_success_state():
    catalog, graph = example()
    text = render_state_graph(graph, catalog)
    assert '| 実行者 | トリガー | 現在の状態 | 成功後の状態 |' in text
    assert '| 001 | 申請審査 | 承認 | 承認者 | 承認操作 | 承認待ち | 承認済み | 承認権限あり | 判断を保存 | w.review/tr.approve |' in text
    assert render_state_graph(graph, catalog) == text
    escaped = replace(graph, transitions=(replace(graph.transitions[0], name='承認|確認\n実行'), *graph.transitions[1:]))
    assert '承認&#124;確認<br>実行' in render_state_graph(escaped, catalog)



def test_flowchart_contains_cycles_and_declared_actors():
    from myworkflow.generation.flowcharts import render_business_flow
    catalog, graph = example()
    diagram = render_business_flow(graph, catalog)
    assert diagram == render_business_flow(graph, catalog)
    assert '実行者：承認者<br/>トリガー：承認操作' in diagram
    assert 'state_0 --> action_2\n    action_2 -->|成功| state_1' in diagram
    assert 'state_1 --> action_3\n    action_3 -->|成功| state_0' in diagram
    assert diagram.count(' -->|成功| ') == len(graph.transitions)
    assert '承認権限あり' not in diagram
    detailed = render_business_flow(graph, catalog, details=True)
    assert '条件：承認権限あり' in detailed
    assert 'パイプライン：判断を保存' in detailed



def test_flowchart_matches_frozen_sample():
    from pathlib import Path
    from examples.feature_demos.declarative_review.contract import compiled
    from myworkflow.generation.flowcharts import render_business_flow
    expected = Path(__file__).resolve().parents[2] / 'examples/feature_demos/declarative_review/docs/flow.md'
    assert render_business_flow(compiled.graphs[0], compiled.catalog) == expected.read_text()



def test_flowchart_labels_cannot_become_mermaid_or_markdown_syntax():
    from myworkflow.generation.flowcharts import render_business_flow
    catalog, graph = example()
    unsafe = '承認" ] --> injected["<script>|`#&\n```\nend'
    replacement = replace(graph.states[0], name=unsafe)
    altered = replace(graph, initial=replacement, states=(replacement, *graph.states[1:]),
                      transitions=tuple(replace(t, source=replacement if t.source is graph.states[0] else t.source,
                                                target=replacement if t.target is graph.states[0] else t.target)
                                        for t in graph.transitions))
    diagram = render_business_flow(altered, catalog)
    assert diagram.count('```') == 2
    assert 'injected[' not in diagram
    assert '<script>' not in diagram
    assert '#34;' in diagram
    assert '#96;#96;#96;<br/>end' in diagram
    assert 'state_0["承認#34;' in diagram



def test_flowchart_rejects_invalid_graph_and_does_not_infer_completion():
    from myworkflow.generation.flowcharts import render_business_flow
    catalog, graph = example()
    with pytest.raises(ContractError, match='initial state'):
        render_business_flow(replace(graph, initial=State('unknown', '不明')), catalog)
    isolated = replace(graph, states=(graph.initial,), transitions=())
    diagram = render_business_flow(isolated, catalog)
    assert 'start --> state_0' in diagram
    assert '成功|' not in diagram
    assert '完了' not in diagram
