"""contracts behavior and invariants."""

from dataclasses import replace
import pytest
from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.state_graph import State, Transition
from tests._support.state_graph import example


def test_cycles_and_symbolic_references_are_exported_without_execution():
    catalog, graph = example()
    result = graph.to_dict(catalog)
    assert result == graph.to_dict(catalog)
    assert result["initial"] == "state.pending"
    assert result["transitions"][2]["target"] == "state.pending"
    assert result["transitions"][0]["binding"] == "b.review"
    assert result["transitions"][0]["actor"] == "role.reviewer"


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda g: replace(g, initial=State("other", "外部")), "initial state"),
        (
            lambda g: replace(g, states=(*g.states, State("p.save", "衝突"))),
            "duplicate graph ID",
        ),
        (lambda g: replace(g, states=(*g.states, g.states[0])), "duplicate graph ID"),
        (
            lambda g: replace(g, states=(*g.states, State("orphan", "未接続"))),
            "unreachable states",
        ),
        (
            lambda g: replace(
                g,
                transitions=(
                    replace(g.transitions[0], target=replace(g.states[2])),
                    *g.transitions[1:],
                ),
            ),
            "undeclared source or target",
        ),
        (
            lambda g: replace(
                g,
                transitions=(
                    replace(g.transitions[0], binding=replace(g.workflow.bindings[0])),
                    *g.transitions[1:],
                ),
            ),
            "binding must belong",
        ),
        (
            lambda g: replace(
                g,
                transitions=(
                    replace(
                        g.transitions[0],
                        trigger=replace(g.transitions[0].trigger, id="other"),
                    ),
                    *g.transitions[1:],
                ),
            ),
            "trigger must belong",
        ),
        (
            lambda g: replace(
                g,
                transitions=(
                    replace(
                        g.transitions[0], trigger=replace(g.transitions[0].trigger)
                    ),
                    *g.transitions[1:],
                ),
            ),
            "trigger must belong",
        ),
        (
            lambda g: replace(
                g,
                transitions=(
                    replace(g.transitions[0], condition=True),
                    *g.transitions[1:],
                ),
            ),
            "condition must be text",
        ),
        (lambda g: replace(g, workflow=replace(g.workflow)), "workflow must belong"),
    ],
)
def test_invalid_graph_is_rejected(mutation, message):
    catalog, graph = example()
    with pytest.raises(ContractError, match=message):
        mutation(graph).validate(catalog)


def test_self_transition_and_renaming_preserve_connection_ids():
    catalog, graph = example()
    pending = graph.states[0]
    self_transition = Transition(
        "tr.stay",
        "確認",
        pending,
        pending,
        graph.workflow.bindings[0],
        graph.workflow.bindings[0].triggers[0],
    )
    revised = replace(graph, transitions=(*graph.transitions, self_transition))
    before = revised.to_dict(catalog)
    after = replace(
        revised,
        transitions=tuple(
            replace(t, name=t.name + "変更") for t in revised.transitions
        ),
    ).to_dict(catalog)
    assert before["transitions"][-1]["source"] == before["transitions"][-1]["target"]
    for original, renamed in zip(
        before["transitions"], after["transitions"], strict=True
    ):
        assert {k: v for k, v in original.items() if k != "name"} == {
            k: v for k, v in renamed.items() if k != "name"
        }
