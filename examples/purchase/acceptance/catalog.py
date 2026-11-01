from pathlib import Path
from examples.purchase import contract as c
from examples.purchase.handlers import registry
from examples.purchase.acceptance.steps import steps
from myworkflow.acceptance.config import AcceptanceConfig
from myworkflow.acceptance.rendering import DocumentOptions

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[2]
program = c.program
DOCUMENTS = DocumentOptions(title='購買フローの受入シナリオ', report_title='購買フローの受入テスト結果',
                            details_link='../../../docs/execution-design.md', data_definitions_link='../data-definitions.md')
CONFIG = AcceptanceConfig(program, steps, tuple(sorted((DIRECTORY / 'features').glob('*.feature'))), ROOT,
                          (ROOT / 'myworkflow', ROOT / 'examples/purchase', ROOT / 'tests', ROOT / 'pyproject.toml'), DOCUMENTS, registry=registry, output_directory=DIRECTORY)


def cases(): return CONFIG.cases()
def implementation_hash(): return CONFIG.implementation_hash()
