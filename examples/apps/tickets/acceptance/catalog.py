from pathlib import Path
from examples.apps.tickets.application import registry
from examples.apps.tickets.contract import SPEC
from examples.apps.tickets.acceptance.steps import steps
from myworkflow.compiler.program import Program
from myworkflow.acceptance.config import AcceptanceConfig
from myworkflow.acceptance import DocumentOptions

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[3]
DOCS = DIRECTORY.parent / 'docs'
CONFIG = AcceptanceConfig(Program(SPEC), steps, tuple((DIRECTORY / 'features').glob('*.feature')), ROOT,
    (ROOT / 'myworkflow', ROOT / 'examples/apps/tickets', ROOT / 'tests', ROOT / 'pyproject.toml'),
    DocumentOptions(title='チケット発行の受入シナリオ', details_link='../../../../docs/architecture.md', features_link='../acceptance/features'),
    registry=registry, output_directory=DOCS)
