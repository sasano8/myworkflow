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
