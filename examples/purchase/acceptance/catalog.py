from pathlib import Path
from examples.purchase.contract import SPEC
from examples.purchase.handlers import registry
from examples.purchase.acceptance.steps import steps
from myworkflow.acceptance.config import AcceptanceConfig
from myworkflow.acceptance.rendering import DocumentOptions
from myworkflow.executable import Program

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[2]
program = Program(SPEC)
DOCUMENTS = DocumentOptions(title='購買フローの受入シナリオ', report_title='購買フローの受入テスト結果',
                            details_link='../../../docs/execution-design.md')
CONFIG = AcceptanceConfig(program, steps, tuple(sorted((DIRECTORY / 'features').glob('*.feature'))), ROOT,
                          (ROOT / 'myworkflow', ROOT / 'examples/purchase', ROOT / 'tests', ROOT / 'pyproject.toml'), DOCUMENTS, registry=registry, output_directory=DIRECTORY)


def cases(): return CONFIG.cases()
def implementation_hash(): return CONFIG.implementation_hash()
