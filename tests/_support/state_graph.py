"""_support behavior and invariants."""

from myworkflow import Trigger, Binding, ContractCatalog, Pipeline, Role, Workflow
from myworkflow.contracts.state_graph import State, StateGraph, Transition


def example():
    pipeline = Pipeline("p.save", "判断を保存", (), (), ())
    binding = Binding(
        "b.review",
        pipeline.id,
        (Trigger("t.review", "承認操作", (), actor_role_id="role.reviewer"),),
        role_mapping=(("system", "role.reviewer"),),
    )
    workflow = Workflow("w.review", "申請審査", (binding,))
    catalog = ContractCatalog(
        (), (pipeline,), (workflow,), (Role("role.reviewer", "審査担当者", "承認者"),)
    )
    pending = State("state.pending", "承認待ち")
    revision = State("state.revision", "修正待ち")
    approved = State("state.approved", "承認済み")
    graph = StateGraph(
        workflow,
        pending,
        (pending, revision, approved),
        (
            Transition(
                "tr.approve",
                "承認",
                pending,
                approved,
                binding,
                binding.triggers[0],
                "承認権限あり",
            ),
            Transition(
                "tr.return", "差戻し", pending, revision, binding, binding.triggers[0]
            ),
            Transition(
                "tr.resubmit", "再申請", revision, pending, binding, binding.triggers[0]
            ),
        ),
    )
    return catalog, graph
