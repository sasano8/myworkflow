from pathlib import Path
from examples.apps.purchase import contract as c
from examples.apps.purchase.handlers import registry
from examples.apps.purchase.acceptance.steps import steps
from myworkflow.acceptance.config import AcceptanceConfig
from myworkflow.acceptance.rendering import DocumentOptions

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[3]
DOCS = DIRECTORY.parent / 'docs'
program = c.program
DOCUMENTS = DocumentOptions(title='購買フローの受入シナリオ', report_title='購買フローの受入テスト結果',
                            details_link='../../../../docs/execution-design.md', data_definitions_link='data-definitions.md', features_link='../acceptance/features')
CONFIG = AcceptanceConfig(program, steps, tuple(sorted((DIRECTORY / 'features').glob('*.feature'))), ROOT,
                          (ROOT / 'myworkflow', ROOT / 'examples/apps/purchase', ROOT / 'tests', ROOT / 'pyproject.toml'), DOCUMENTS, registry=registry, output_directory=DOCS)


def cases(): return CONFIG.cases()
def implementation_hash(): return CONFIG.implementation_hash()
