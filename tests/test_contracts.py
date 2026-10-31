"""Declaration API tests use synthetic data; purchase requirements live in contract.py."""
from dataclasses import replace
import unittest

from myworkflow import Artifact, Binding, Catalog, Lock, Pipeline, Role, Step, Trigger, Use, Workflow, render


def small_catalog():
    return Catalog(
        artifacts=(Artifact('a.input', '入力値'), Artifact('a.output', '処理結果')),
        pipelines=(Pipeline('p.convert', '変換', ('a.input',), ('a.output',), (
            Lock('s.lock', '排他制御', ('a.input',)),
            Step('s.convert', '値の変換', '入力値を整形する。', (Use('a.input', '参照'), Use('a.output', '保持'))),
        )),),
        workflows=(
            Workflow('w.first', '受付', (Binding('b.first', 'p.convert', '入力イベント', (('a.input', '本文'),),
                next_workflow_id='w.second', actor_role_id='role.operator', role_mapping=(('system', 'role.system'),),
                additional_triggers=(Trigger('t.timer', '指定日時', (('a.input', '待機情報'),),
                                             wait='予定時刻に到達', actor_role_id='role.system'),)),)),
            Workflow('w.second', '後続', (Binding('b.second', 'p.convert', '内部イベント', (('a.input', 'イベント'),),
                actor_role_id='role.system', role_mapping=(('system', 'role.system'),)),)),
        ),
        roles=(Role('role.operator', '入力担当部署の担当者', '操作者'), Role('role.system', '処理システム', 'システム')),
    )


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.catalog = small_catalog()

    def first_binding(self, **changes):
        w = self.catalog.workflows[0]
        return replace(self.catalog, workflows=(replace(w, bindings=(replace(w.bindings[0], **changes),)), self.catalog.workflows[1]))

    def test_declarations_render_deterministically(self):
        text = render(self.catalog)
        self.assertEqual(text, render(self.catalog))
        self.assertIn('| 001-00001-00002 | — | システム | 値の変換 | 入力値を整形する。 | — | 参照：入力値／保持：処理結果 | w.first/b.first/p.convert/s.convert |', text)
        self.assertIn('入力：入力値', text)
        self.assertIn('出力：処理結果', text)

    def test_reuse_has_distinct_placement_identity_and_shared_definition(self):
        text = render(self.catalog)
        self.assertIn('w.first/b.first/p.convert/s.convert', text)
        self.assertIn('w.second/b.second/p.convert/s.convert', text)

    def test_multiple_triggers_share_steps_but_not_receipt_identity(self):
        section = render(self.catalog).split('## 002', 1)[0]
        self.assertEqual(section.count('| 001-00001-00000 |'), 2)
        self.assertIn('トリガー1：入力イベント', section)
        self.assertIn('トリガー2：指定日時', section)
        self.assertEqual(section.count('| 値の変換 |'), 1)
        self.assertIn('w.first/b.first/p.convert/request |', section)
        self.assertIn('w.first/b.first/p.convert/request/t.timer', section)

    def test_additional_trigger_contract_is_validated(self):
        b = self.catalog.workflows[0].bindings[0]
        t = b.additional_triggers[0]
        for invalid in (replace(t, input_mapping=()), replace(t, id=b.id), replace(t, after=b.id)):
            with self.subTest(trigger=invalid), self.assertRaises(ValueError):
                render(self.first_binding(additional_triggers=(invalid,)))

    def test_rename_and_reorder_preserve_ids(self):
        first, second = self.catalog.workflows
        text = render(replace(self.catalog, workflows=(second, replace(first, name='変更後'))))
        self.assertIn('w.first/b.first/p.convert/s.convert', text)
        self.assertIn('002-00001-00002', text)
        self.assertIn('変更後', text)

    def test_invalid_references_and_contracts(self):
        p = self.catalog.pipelines[0]
        cases = [
            replace(self.catalog, artifacts=self.catalog.artifacts + (self.catalog.artifacts[0],)),
            replace(self.catalog, pipelines=(replace(p, inputs=('missing',)),)),
            replace(self.catalog, pipelines=(replace(p, reply=False),)),
            replace(self.catalog, pipelines=(replace(p, steps=(replace(p.steps[1], uses=(Use('a.input', 'invalid'),)),)),)),
        ]
        for changes in ({'input_mapping': ()}, {'pipeline_id': 'missing'}, {'after': 'b.first'}, {'next_workflow_id': 'missing'}):
            cases.append(self.first_binding(**changes))
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError): render(case)

    def test_markdown_escaping(self):
        artifact = replace(self.catalog.artifacts[0], name='入力|明細\n<script>')
        text = render(replace(self.catalog, artifacts=(artifact, self.catalog.artifacts[1])))
        self.assertIn('入力&#124;明細<br>&lt;script&gt;', text)
        self.assertNotIn('<script>', text)

    def test_roles_show_operator_and_system_separately(self):
        text = render(self.catalog)
        self.assertIn('| role.operator | 入力担当部署の担当者 | 操作者 |', text)
        self.assertIn('| 操作者 | 受付 |', text)
        self.assertIn('| システム | 値の変換 |', text)

    def test_abstract_step_role_can_be_bound_at_placement(self):
        p = self.catalog.pipelines[0]
        step = replace(p.steps[1], actor='processor')
        catalog = self.first_binding(role_mapping=(('system', 'role.system'), ('processor', 'role.operator')))
        w = catalog.workflows[1]
        second = replace(w.bindings[0], role_mapping=(('system', 'role.system'), ('processor', 'role.system')))
        catalog = replace(catalog, pipelines=(replace(p, steps=(p.steps[0], step)),), workflows=(catalog.workflows[0], replace(w, bindings=(second,))))
        self.assertIn('| 操作者 | 値の変換 |', render(catalog))
        self.assertEqual(p.steps[1].actor, 'system')

    def test_invalid_roles_are_rejected(self):
        for changes in ({'actor_role_id': 'missing'}, {'role_mapping': ()},
                        {'role_mapping': (('system', 'missing'),)},
                        {'role_mapping': (('system', 'role.system'), ('system', 'role.operator'))}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): render(self.first_binding(**changes))
        t = replace(self.catalog.workflows[0].bindings[0].additional_triggers[0], actor_role_id='missing')
        with self.assertRaises(ValueError): render(self.first_binding(additional_triggers=(t,)))

    def test_artifact_operations_and_boundaries_are_visible(self):
        text = render(self.catalog)
        self.assertIn('参照：入力値／保持：処理結果', text)
        self.assertIn('入力：入力値', text)
        self.assertIn('出力：処理結果', text)
        self.assertNotIn('起動定義なし', text)

    def test_wait_lock_and_no_reply_are_visible(self):
        p = replace(self.catalog.pipelines[0], reply=False, outputs=())
        text = render(replace(self.catalog, pipelines=(p,)))
        for expected in ('待機・再開条件：予定時刻に到達', '次ワークフロー起動：後続', '異常終了を含む',
                         '参照：入力値／保持：排他キー・ロック', '出力：なし（応答不要）'):
            self.assertIn(expected, text)


if __name__ == '__main__':
    unittest.main()
