"""Business acceptance scenarios for the purchase sample."""
from pathlib import Path
import pytest
from pytest_bdd import scenarios

pytest_plugins = ["examples.purchase.acceptance.steps"]
pytestmark = pytest.mark.acceptance_config("examples.purchase.acceptance.catalog")

scenarios(str(Path(__file__).resolve().parents[2] / 'examples/purchase/acceptance/features'))
