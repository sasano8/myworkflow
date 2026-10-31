from pathlib import Path
from types import SimpleNamespace
import pytest
from pytest_bdd import scenarios
from examples.tickets.application import engine

pytest_plugins = ['examples.tickets.acceptance.steps']
pytestmark = pytest.mark.acceptance_config('examples.tickets.acceptance.catalog')
scenarios(str(Path(__file__).resolve().parents[2] / 'examples/tickets/acceptance/features/tickets.feature'))


@pytest.fixture
def ctx(tmp_path):
    return SimpleNamespace(engine=engine(tmp_path / 'tickets.db'))
