"""State declarations are inspected without invoking any business handler."""
from dataclasses import replace

import pytest

from myworkflow import Binding, ContractCatalog, Pipeline, Role, Workflow
from myworkflow.errors import ContractError
from myworkflow.state_graph import State, StateGraph, Transition, render_state_graph


def example():
    pipeline = Pipeline('p.save', '判断を保存', (), (), ())
    binding = Binding('b.review', pipeline.id, '承認操作', (), actor_role_id='role.reviewer', role_mapping=(('system', 'role.reviewer'),))
    workflow = Workflow('w.review', '申請審査', (binding,))
    catalog = ContractCatalog((), (pipeline,), (workflow,), (Role('role.reviewer', '審査担当者', '承認者'),))
    pending = State('state.pending', '承認待ち')
    revision = State('state.revision', '修正待ち')
    approved = State('state.approved', '承認済み')
    graph = StateGraph(workflow, pending, (pending, revision, approved), (
        Transition('tr.approve', '承認', pending, approved, binding, binding.triggers[0], '承認権限あり'),
        Transition('tr.return', '差戻し', pending, revision, binding, binding.triggers[0]),
        Transition('tr.resubmit', '再申請', revision, pending, binding, binding.triggers[0]),
    ))
    return catalog, graph


def test_cycles_and_symbolic_references_are_exported_without_execution():
    catalog, graph = example()
    result = graph.to_dict(catalog)
    assert result == graph.to_dict(catalog)
    assert result['initial'] == 'state.pending'
    assert result['transitions'][2]['target'] == 'state.pending'
    assert result['transitions'][0]['binding'] == 'b.review'
    assert result['transitions'][0]['actor'] == 'role.reviewer'


def test_render_column_order_and_success_state():
    catalog, graph = example()
    text = render_state_graph(graph, catalog)
    assert '| 実行者 | トリガー | 現在の状態 | 成功後の状態 |' in text
    assert '| 001 | 申請審査 | 承認 | 承認者 | 承認操作 | 承認待ち | 承認済み | 承認権限あり | 判断を保存 | w.review/tr.approve |' in text
    assert render_state_graph(graph, catalog) == text
    escaped = replace(graph, transitions=(replace(graph.transitions[0], name='承認|確認\n実行'), *graph.transitions[1:]))
    assert '承認&#124;確認<br>実行' in render_state_graph(escaped, catalog)


@pytest.mark.parametrize('mutation, message', [
    (lambda g: replace(g, initial=State('other', '外部')), 'initial state'),
    (lambda g: replace(g, states=(*g.states, State('p.save', '衝突'))), 'duplicate graph ID'),
    (lambda g: replace(g, states=(*g.states, g.states[0])), 'duplicate graph ID'),
    (lambda g: replace(g, states=(*g.states, State('orphan', '未接続'))), 'unreachable states'),
    (lambda g: replace(g, transitions=(replace(g.transitions[0], target=replace(g.states[2])), *g.transitions[1:])), 'undeclared source or target'),
    (lambda g: replace(g, transitions=(replace(g.transitions[0], binding=replace(g.workflow.bindings[0])), *g.transitions[1:])), 'binding must belong'),
    (lambda g: replace(g, transitions=(replace(g.transitions[0], trigger=replace(g.transitions[0].trigger, id='other')), *g.transitions[1:])), 'trigger must belong'),
    (lambda g: replace(g, transitions=(replace(g.transitions[0], condition=True), *g.transitions[1:])), 'condition must be text'),
    (lambda g: replace(g, workflow=replace(g.workflow)), 'workflow must belong'),
])
def test_invalid_graph_is_rejected(mutation, message):
    catalog, graph = example()
    with pytest.raises(ContractError, match=message):
        mutation(graph).validate(catalog)


def test_self_transition_and_renaming_preserve_connection_ids():
    catalog, graph = example()
    pending = graph.states[0]
    self_transition = Transition('tr.stay', '確認', pending, pending,
                                 graph.workflow.bindings[0], graph.workflow.bindings[0].triggers[0])
    revised = replace(graph, transitions=(*graph.transitions, self_transition))
    before = revised.to_dict(catalog)
    after = replace(revised, transitions=tuple(replace(t, name=t.name + '変更') for t in revised.transitions)).to_dict(catalog)
    assert before['transitions'][-1]['source'] == before['transitions'][-1]['target']
    for original, renamed in zip(before['transitions'], after['transitions'], strict=True):
        assert {k: v for k, v in original.items() if k != 'name'} == {k: v for k, v in renamed.items() if k != 'name'}


def test_flowchart_contains_cycles_and_declared_actors():
    from myworkflow.flowchart import render_business_flow
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
    from examples.declarative_review import compiled
    from myworkflow.flowchart import render_business_flow
    expected = Path(__file__).resolve().parents[1] / 'examples/declarative_review-flow.md'
    assert render_business_flow(compiled.graphs[0], compiled.catalog) == expected.read_text()


def test_flowchart_labels_cannot_become_mermaid_or_markdown_syntax():
    from myworkflow.flowchart import render_business_flow
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
    from myworkflow.flowchart import render_business_flow
    catalog, graph = example()
    with pytest.raises(ContractError, match='initial state'):
        render_business_flow(replace(graph, initial=State('unknown', '不明')), catalog)
    isolated = replace(graph, states=(graph.initial,), transitions=())
    diagram = render_business_flow(isolated, catalog)
    assert 'start --> state_0' in diagram
    assert '成功|' not in diagram
    assert '完了' not in diagram
