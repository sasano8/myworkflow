from pathlib import Path
from types import SimpleNamespace
import pytest
from pytest_bdd import scenarios
from examples.apps.tickets.application import engine

pytest_plugins = ['examples.apps.tickets.acceptance.steps']
pytestmark = pytest.mark.acceptance_config('examples.apps.tickets.acceptance.catalog')
scenarios(str(Path(__file__).resolve().parents[2] / 'examples/apps/tickets/acceptance/features/tickets.feature'))


@pytest.fixture
def ctx(tmp_path):
    return SimpleNamespace(engine=engine(tmp_path / 'tickets.db'))
