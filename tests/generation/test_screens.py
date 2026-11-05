"""Screen inventory preserves entry-point relationships and local-only actions."""

from dataclasses import replace

import pytest

from examples.apps.purchase.contract import program
from examples.apps.purchase.screens import SCREENS
from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.screens import (
    Screen,
    ScreenFeature,
    WorkflowCall,
    validate_screens,
)
from myworkflow.generation.screens import render_screens


def test_purchase_screens_show_gestures_and_distinct_workflow_entry_points():
    text = render_screens(SCREENS, program.model)
    assert '<a id="screen.purchase_entry"></a>' in text
    assert "金額欄の値を変更する | 画面単体" in text
    row = next(
        line
        for line in text.splitlines()
        if line.startswith("| feature.purchase_reset |")
    )
    assert row.endswith("| — | — | — | — |")
    submit = next(
        line
        for line in text.splitlines()
        if line.startswith("| feature.purchase_submit |")
    )
    approve = next(
        line
        for line in text.splitlines()
        if line.startswith("| feature.purchase_approve |")
    )
    assert "申請ボタンを押す" in submit
    assert "実行ボタンを押す" in approve
    assert (
        "(workflows/w.approval.md)" in submit and "(workflows/w.approval.md)" in approve
    )
    assert "| b.submit | t.submit | [申請者]" in submit
    assert "| b.approve | t.approve | [承認者]" in approve
    assert text == render_screens(SCREENS, program.model)


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (WorkflowCall("w.unknown", "b.submit", "t.submit"), "unknown workflow"),
        (WorkflowCall("w.attach", "b.submit", "t.submit"), "binding does not belong"),
        (
            WorkflowCall("w.approval", "b.submit", "t.approve"),
            "trigger does not belong",
        ),
    ],
)
def test_call_must_reference_an_entry_point_of_the_selected_workflow(call, message):
    feature = replace(SCREENS[0].features[-1], workflow_call=call)
    with pytest.raises(ContractError, match=message):
        render_screens((replace(SCREENS[0], features=(feature,)),), program.model)


def test_screen_and_feature_ids_are_unique_and_gestures_are_required():
    with pytest.raises(ContractError, match="unique"):
        validate_screens((SCREENS[0], SCREENS[0]), program.model)
    feature = SCREENS[0].features[0]
    with pytest.raises(ContractError, match="unique"):
        validate_screens(
            (replace(SCREENS[0], features=(feature, feature)),), program.model
        )
    with pytest.raises(ContractError, match="event is required"):
        validate_screens(
            (replace(SCREENS[0], features=(replace(feature, event=" "),)),),
            program.model,
        )


def test_empty_screens_and_table_labels_are_explicit_and_escaped():
    assert "画面は未定義。" in render_screens((), program.model)
    assert "画面機能は未定義。" in render_screens(
        (Screen("screen.empty", "未定義", ()),), program.model
    )
    screen = Screen(
        "screen.escape",
        "入力|画面",
        (ScreenFeature("feature.escape", "入力", "変更\n時", "<入力>を表示"),),
    )
    text = render_screens((screen,), program.model)
    assert "入力&#124;画面" in text
    assert "変更<br>時" in text
    assert "&lt;入力&gt;を表示" in text
