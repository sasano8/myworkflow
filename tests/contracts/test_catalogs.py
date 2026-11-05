"""Requirement catalogs are namespaces; a root only groups and selects them."""

from dataclasses import replace

import pytest

from examples.feature_demos.product_catalogs.root import ROOT, insurance, loan
from myworkflow import ContractCatalog, RootCatalog
from myworkflow.contracts.errors import ContractError


def test_root_selects_same_local_workflow_id_from_independent_catalogs():
    ROOT.validate()
    assert ROOT.catalog("product.insurance") is insurance
    assert ROOT.workflow("product.insurance", "w.main") is insurance.workflows[0]
    assert ROOT.workflow("product.loan", "w.main") is loan.workflows[0]
    assert insurance.workflows[0].name != loan.workflows[0].name
    assert insurance.roles[0] is loan.roles[0]
    assert len(insurance.pipelines[0].steps) == 3
    assert len(loan.pipelines[0].steps) == 2
    with pytest.raises(ContractError, match="unknown catalog"):
        ROOT.workflow("product.unknown", "w.main")
    with pytest.raises(ContractError, match="product.loan: unknown workflow"):
        ROOT.workflow("product.loan", "w.unknown")


def test_duplicate_local_definitions_and_catalog_ids_are_rejected():
    with pytest.raises(ContractError, match="duplicate catalog"):
        replace(ROOT, catalogs=(insurance, insurance)).validate()
    broken = replace(loan, pipelines=loan.pipelines * 2)
    with pytest.raises(ContractError, match="org.example/product.loan"):
        replace(ROOT, catalogs=(insurance, broken)).validate()


def test_internal_references_never_fall_back_to_another_catalog():
    private = replace(insurance.pipelines[0], id="p.insurance_only", steps=())
    first = replace(insurance, pipelines=(*insurance.pipelines, private))
    workflow = loan.workflows[0]
    binding = replace(workflow.bindings[0], pipeline_id=private.id)
    second = replace(loan, workflows=(replace(workflow, bindings=(binding,)),))
    with pytest.raises(
        ContractError, match="org.example/product.loan: Unknown pipeline"
    ):
        replace(ROOT, catalogs=(first, second)).validate()


@pytest.mark.parametrize(
    ("identity", "name"),
    [("", "保険"), ("product.insurance", ""), ("../insurance", "保険"), ([], "保険")],
)
def test_named_catalog_metadata_is_validated(identity, name):
    with pytest.raises(ValueError, match="Catalog requires"):
        replace(insurance, id=identity, name=name).validate()


def test_legacy_standalone_catalogs_remain_valid_but_root_children_need_names():
    legacy = ContractCatalog((), (), ())
    legacy.validate()
    with pytest.raises(ContractError, match="child catalog requires"):
        RootCatalog("root", "組織", (legacy,)).validate()
    RootCatalog("root", "組織", ()).validate()
