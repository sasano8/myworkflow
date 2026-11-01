"""Declaration API tests use synthetic data; purchase requirements live in contract.py."""
from dataclasses import replace
import pytest

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


class TestContracts:
    @pytest.fixture(autouse=True)
    def prepare(self):
        self.catalog = small_catalog()

    def first_binding(self, **changes):
        w = self.catalog.workflows[0]
        return replace(self.catalog, workflows=(replace(w, bindings=(replace(w.bindings[0], **changes),)), self.catalog.workflows[1]))

    def test_declarations_render_deterministically(self):
        text = render(self.catalog)
        assert text == render(self.catalog)
        assert '| 001-00001-00002 | — | システム | 値の変換 | 入力値を整形する。 | — | 参照：入力値／保持：処理結果 | w.first/b.first/p.convert/s.convert |' in text
        assert '入力：入力値' in text
        assert '出力：終了コード・メッセージ' in text
        assert '保持：処理結果' in text

    def test_reuse_has_distinct_placement_identity_and_shared_definition(self):
        text = render(self.catalog)
        assert 'w.first/b.first/p.convert/s.convert' in text
        assert 'w.second/b.second/p.convert/s.convert' in text

    def test_multiple_triggers_share_steps_but_not_receipt_identity(self):
        section = render(self.catalog).split('## 002', 1)[0]
        assert section.count('| 001-00001-00000 |') == 2
        assert 'トリガー1：入力イベント' in section
        assert 'トリガー2：指定日時' in section
        assert section.count('| 値の変換 |') == 1
        assert 'w.first/b.first/p.convert/request |' in section
        assert 'w.first/b.first/p.convert/request/t.timer' in section

    @pytest.mark.parametrize("case_index", range(3), ids=["missing-input", "duplicate-id", "self-after"])
    def test_additional_trigger_contract_is_validated(self, case_index):
        b = self.catalog.workflows[0].bindings[0]
        t = b.additional_triggers[0]
        invalid = (replace(t, input_mapping=()), replace(t, id=b.id), replace(t, after=b.id))[case_index]
        with pytest.raises(ValueError):
            render(self.first_binding(additional_triggers=(invalid,)))

    def test_rename_and_reorder_preserve_ids(self):
        first, second = self.catalog.workflows
        text = render(replace(self.catalog, workflows=(second, replace(first, name='変更後'))))
        assert 'w.first/b.first/p.convert/s.convert' in text
        assert '002-00001-00002' in text
        assert '変更後' in text

    @pytest.mark.parametrize('case_index', range(8), ids=[
        'duplicate-artifact', 'unknown-input', 'no-reply-output', 'unknown-operation',
        'missing-mapping', 'unknown-pipeline', 'self-after', 'unknown-workflow',
    ])
    def test_invalid_references_and_contracts(self, case_index):
        p = self.catalog.pipelines[0]
        cases = [
            replace(self.catalog, artifacts=self.catalog.artifacts + (self.catalog.artifacts[0],)),
            replace(self.catalog, pipelines=(replace(p, inputs=('missing',)),)),
            replace(self.catalog, pipelines=(replace(p, reply="invalid"),)),
            replace(self.catalog, pipelines=(replace(p, steps=(replace(p.steps[1], uses=(Use('a.input', 'invalid'),)),)),)),
        ]
        for changes in ({'input_mapping': ()}, {'pipeline_id': 'missing'}, {'after': 'b.first'}, {'next_workflow_id': 'missing'}):
            cases.append(self.first_binding(**changes))
        case = cases[case_index]
        with pytest.raises(ValueError): render(case)

    def test_markdown_escaping(self):
        artifact = replace(self.catalog.artifacts[0], name='入力|明細\n<script>')
        text = render(replace(self.catalog, artifacts=(artifact, self.catalog.artifacts[1])))
        assert '入力&#124;明細<br>&lt;script&gt;' in text
        assert '<script>' not in text

    def test_roles_show_operator_and_system_separately(self):
        text = render(self.catalog)
        assert '| role.operator | 入力担当部署の担当者 | 操作者 |' in text
        assert '| 操作者 | 受付 |' in text
        assert '| システム | 値の変換 |' in text

    def test_abstract_step_role_can_be_bound_at_placement(self):
        p = self.catalog.pipelines[0]
        step = replace(p.steps[1], actor='processor')
        catalog = self.first_binding(role_mapping=(('system', 'role.system'), ('processor', 'role.operator')))
        w = catalog.workflows[1]
        second = replace(w.bindings[0], role_mapping=(('system', 'role.system'), ('processor', 'role.system')))
        catalog = replace(catalog, pipelines=(replace(p, steps=(p.steps[0], step)),), workflows=(catalog.workflows[0], replace(w, bindings=(second,))))
        assert '| 操作者 | 値の変換 |' in render(catalog)
        assert p.steps[1].actor == 'system'

    @pytest.mark.parametrize('changes', [
        pytest.param({'actor_role_id': 'missing'}, id='unknown-actor'),
        pytest.param({'role_mapping': ()}, id='missing-slot'),
        pytest.param({'role_mapping': (('system', 'missing'),)}, id='unknown-role'),
        pytest.param({'role_mapping': (('system', 'role.system'), ('system', 'role.operator'))}, id='duplicate-slot'),
    ])
    def test_invalid_roles_are_rejected(self, changes):
        with pytest.raises(ValueError): render(self.first_binding(**changes))

    def test_additional_trigger_with_unknown_role_is_rejected(self):
        t = replace(self.catalog.workflows[0].bindings[0].additional_triggers[0], actor_role_id='missing')
        with pytest.raises(ValueError): render(self.first_binding(additional_triggers=(t,)))

    def test_artifact_operations_and_boundaries_are_visible(self):
        text = render(self.catalog)
        assert '参照：入力値／保持：処理結果' in text
        assert '入力：入力値' in text
        assert '出力：終了コード・メッセージ' in text
        assert '保持：処理結果' in text
        assert '起動定義なし' not in text

    def test_wait_lock_and_no_reply_are_visible(self):
        p = replace(self.catalog.pipelines[0], reply=False, outputs=())
        text = render(replace(self.catalog, pipelines=(p,)))
        for expected in ('待機・再開条件：予定時刻に到達', '次ワークフロー起動：後続', '異常終了を含む',
                         '参照：入力値／保持：排他キー・ロック', '出力：なし（応答不要）'):
            assert expected in text
