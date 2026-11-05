"""Root navigation groups product catalogs without merging their definitions."""

from myworkflow import RootCatalog
from .insurance import CATALOG as insurance
from .loan import CATALOG as loan

ROOT = RootCatalog("org.example", "サンプル銀行", (insurance, loan))

# Both resolve w.main, explicitly selecting the requirement catalog first.
insurance_workflow = ROOT.workflow("product.insurance", "w.main")
loan_workflow = ROOT.workflow("product.loan", "w.main")
