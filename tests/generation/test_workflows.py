"""Workflow pages must preserve shared relationships and expose missing coverage."""
from dataclasses import replace
from types import SimpleNamespace
import re
from pathlib import PurePosixPath
from urllib.parse import unquote

from examples.feature_demos.declarative_review.contract import compiled
from myworkflow import Pipeline, Role, Workflow
from myworkflow.generation.workflows import workflow_documents


def test_shared_pipeline_is_defined_once_and_each_placement_is_navigable():
    docs = workflow_documents(compiled.catalog, graphs=compiled.graphs)
    page = docs['workflows/w.review.md']
    assert page.count('処理：[p.review_submit]') == 2
    assert docs['shared-definitions.md'].count('## p.review_submit：') == 1
    assert 'tr.review_resubmit' in page
    assert 'state.review_revising' in page
    assert 'b.review_resubmit/t.review_resubmit' in page
    assert '## 受入条件\n\n未定義。' in page
    for name, text in docs.items():
        for target in re.findall(r'\]\(([^)]+)\)', text):
            path, _, fragment = target.partition('#')
            parts = []
            for part in (PurePosixPath(name).parent / unquote(path)).parts:
                if part == '..':
                    parts.pop()
                elif part != '.':
                    parts.append(part)
            destination = '/'.join(parts)
            assert destination in docs, (name, target)
            if fragment:
                assert f'id="{fragment}"' in docs[destination], (name, target)


def test_unplaced_definitions_and_exact_acceptance_targets_are_visible():
    catalog = replace(compiled.catalog,
                      pipelines=(*compiled.catalog.pipelines, Pipeline('p.unplaced', '未配置処理', (), (), ())),
                      roles=(*compiled.catalog.roles, Role('role.unused', '未使用', '未使用')))
    cases = (SimpleNamespace(id='case.shared', name='共有処理', requirements=('p.review_submit',)),
             SimpleNamespace(id='case.orphan', name='対象未配置', requirements=('p.unplaced',)))
    docs = workflow_documents(catalog, cases=cases)
    assert 'p.unplaced' in docs['workflows.md']
    assert 'role.unused' in docs['workflows.md']
    assert 'case.orphan' in docs['workflows.md']
    page = docs['workflows/w.review.md']
    assert 'case.shared' in page
    assert 'case.orphan' not in page
    assert '## 状態・遷移\n\n未定義。' in page
    assert docs == workflow_documents(catalog, cases=cases)


def test_index_callers_come_from_triggers_and_link_to_sample_roles():
    docs = workflow_documents(compiled.catalog)
    row = next(line for line in docs['workflows.md'].splitlines() if line.startswith('| w.review |'))
    assert '| 呼び出すロール |' in docs['workflows.md']
    assert row.count('[申請者](shared-definitions.md#role.requester)') == 1
    assert row.count('[承認者](shared-definitions.md#role.approver)') == 1
    assert 'role.system' not in row  # Internal step executor is not a caller.
    assert row.index('role.requester') < row.index('role.approver')

    from examples.apps.purchase.contract import program
    purchase = workflow_documents(program.model)['workflows.md']
    approval = next(line for line in purchase.splitlines() if line.startswith('| w.approval |'))
    assert '[システム](shared-definitions.md#role.system)' in approval
    assert '[発注担当者](shared-definitions.md#role.buyer)' in approval

    empty = replace(compiled.catalog, workflows=(Workflow('w.empty', '未定義の起動', ()),))
    row = next(line for line in workflow_documents(empty)['workflows.md'].splitlines() if line.startswith('| w.empty |'))
    assert '| 未定義 | 0 |' in row
