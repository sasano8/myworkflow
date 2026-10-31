from dataclasses import replace
from pathlib import Path
import unittest

from examples.approval import catalog
from myworkflow import Artifact, Use, render


class ContractTests(unittest.TestCase):
    def test_sample_matches_exactly(self):
        expected = Path(__file__).resolve().parents[1] / "examples" / "approval.md"
        self.assertEqual(render(catalog), expected.read_text(encoding="utf-8"))
        self.assertEqual(render(catalog), render(catalog))

    def test_reuse_has_distinct_placement_identity_and_shared_definition(self):
        text = render(catalog)
        self.assertIn("w.approval/b.timer/p.dispatch/s.dispatch", text)
        self.assertIn("w.manual/b.manual/p.dispatch/s.dispatch", text)
        self.assertIn("指定日時に到達", text)
        self.assertIn("ユーザーがFEで実行", text)

    def test_multiple_triggers_share_steps_but_not_receipt_identity(self):
        text = render(catalog)
        section = text.split("### 001-00003 実行開始", 1)[1].split("## 002", 1)[0]
        self.assertEqual(section.count("| 001-00003-00000 |"), 2)
        self.assertIn("トリガー1：指定日時に到達", section)
        self.assertIn("トリガー2：承認済み申請をユーザーがFEで実行", section)
        self.assertEqual(section.count("| 実行引継ぎ |"), 1)
        self.assertIn("w.approval/b.timer/p.dispatch/request |", section)
        self.assertIn("w.approval/b.timer/p.dispatch/request/t.approved-manual", section)
        self.assertIn("承認済みであること", section)

    def test_additional_trigger_contract_is_validated(self):
        w = catalog.workflows[0]
        b = w.bindings[2]
        t = b.additional_triggers[0]
        for invalid in (replace(t, input_mapping=()), replace(t, id=b.id), replace(t, after=b.id)):
            modified = replace(b, additional_triggers=(invalid,))
            case = replace(catalog, workflows=(replace(w, bindings=(*w.bindings[:2], modified)), *catalog.workflows[1:]))
            with self.subTest(trigger=invalid), self.assertRaises(ValueError):
                render(case)

    def test_rename_and_reorder_preserve_ids(self):
        renamed = replace(catalog.workflows[0], name="変更後")
        modified = replace(catalog, workflows=(catalog.workflows[1], renamed, catalog.workflows[2]))
        text = render(modified)
        self.assertIn("w.approval/b.timer/p.dispatch/s.dispatch", text)
        self.assertIn("002-00003-00001", text)
        self.assertIn("変更後", text)

    def test_invalid_references_and_contracts(self):
        p = catalog.pipelines[0]
        b = catalog.workflows[0].bindings[0]
        invalid = [
            replace(catalog, artifacts=catalog.artifacts + (catalog.artifacts[0],)),
            replace(catalog, pipelines=(replace(p, inputs=("missing",)),)),
            replace(catalog, pipelines=(replace(p, reply=False),)),
            replace(catalog, pipelines=(replace(p, steps=(replace(p.steps[0], uses=(Use("a.id", "invalid"),)),)),)),
        ]
        for binding in [replace(b, input_mapping=()), replace(b, pipeline_id="missing"), replace(b, after=b.id), replace(b, next_workflow_id="missing")]:
            invalid.append(replace(catalog, workflows=(replace(catalog.workflows[0], bindings=(binding,)),)))
        for case in invalid:
            with self.subTest(case=case), self.assertRaises(ValueError):
                render(case)

    def test_markdown_escaping(self):
        a = replace(catalog.artifacts[0], name="申請|明細\n<script>")
        text = render(replace(catalog, artifacts=(a,) + catalog.artifacts[1:]))
        self.assertIn("申請&#124;明細<br>&lt;script&gt;", text)
        self.assertNotIn("<script>", text)

    def test_wait_lock_and_no_reply_are_visible(self):
        text = render(catalog)
        for expected in ("待機・再開条件", "次ワークフロー起動：申請実行", "異常終了を含む", "参照：申請ID／保持：排他キー・ロック", "出力：なし（応答不要）"):
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
