"""Product navigation preserves local definitions and all generated links."""
from dataclasses import replace
from pathlib import PurePosixPath
import re

from examples.feature_demos.product_catalogs.root import ROOT, insurance
from myworkflow.generation.catalogs import root_catalog_documents


def test_catalog_documents_are_separate_deterministic_and_navigable():
    docs = root_catalog_documents(ROOT)
    assert docs == root_catalog_documents(ROOT)
    first = docs['catalogs/product.insurance/shared-definitions.md']
    second = docs['catalogs/product.loan/shared-definitions.md']
    assert '保険料の算定' in first and '返済計画の計算' not in first
    assert '返済計画の計算' in second and '保険料の算定' not in second
    for name, text in docs.items():
        for link in re.findall(r'\]\(([^)]+)\)', text):
            path, _, fragment = link.partition('#')
            parts = []
            for part in (PurePosixPath(name).parent / path).parts:
                if part == '..':
                    parts.pop()
                elif part != '.':
                    parts.append(part)
            target = '/'.join(parts)
            assert target in docs, (name, link)
            if fragment:
                assert f'id="{fragment}"' in docs[target], (name, link)


def test_root_catalog_with_value_definitions_includes_local_data_documents():
    from examples.feature_demos.approval_values.application import compiled
    catalog = replace(compiled.catalog, id=insurance.id, name=insurance.name)
    docs = root_catalog_documents(replace(ROOT, catalogs=(catalog,)))
    prefix = 'catalogs/product.insurance/'
    assert prefix + 'data-definitions.md' in docs
    assert prefix + 'data-definitions.json' in docs
    assert '(data-definitions.md#' in docs[prefix + 'shared-definitions.md']


def test_empty_root_is_explicit():
    assert '要求カタログは未定義。' in root_catalog_documents(replace(ROOT, catalogs=()))['catalogs.md']


def test_overview_tracks_catalog_changes_without_sample_specific_prose():
    renamed = replace(insurance, name='新商品', workflows=(replace(insurance.workflows[0], name='新しい業務'),),
                      pipelines=(replace(insurance.pipelines[0], name='新しい処理', steps=()),))
    docs = root_catalog_documents(replace(ROOT, name='別の組織', catalogs=(renamed,)))
    overview = docs['overview.md']
    assert '# 別の組織：業務要求の概要' in overview
    assert '新商品' in overview and '新しい業務' in overview and '新しい処理' in overview
    assert 'サンプル銀行' not in overview and '保険料' not in overview and '融資' not in overview
    assert '業務担当者' not in overview
    assert '共有ロールは未定義。' in overview
    assert '未定義' in overview  # No steps are declared in the changed catalog.


def test_same_role_ids_do_not_imply_shared_role_definitions():
    second = replace(insurance, id='product.other', roles=tuple(replace(r) for r in insurance.roles))
    overview = root_catalog_documents(replace(ROOT, catalogs=(insurance, second)))['overview.md']
    assert '共有ロールは未定義。' in overview


def test_root_documents_are_byte_identical_across_processes_and_hash_seeds():
    import os
    from pathlib import Path
    import subprocess
    import sys

    code = '''import json
from examples.feature_demos.product_catalogs.root import ROOT
from myworkflow.generation.catalogs import root_catalog_documents
print(json.dumps(root_catalog_documents(ROOT), ensure_ascii=False, sort_keys=True))
'''
    outputs = [subprocess.check_output([sys.executable, '-c', code],
                cwd=Path(__file__).resolve().parents[2],
                env={**os.environ, 'PYTHONHASHSEED': seed}) for seed in ('1', '738')]
    assert outputs[0] == outputs[1]
