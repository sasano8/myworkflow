"""Business acceptance scenarios for the purchase sample."""

from pathlib import Path
import pytest
from pytest_bdd import scenarios

pytest_plugins = ["examples.apps.purchase.acceptance.steps"]
pytestmark = pytest.mark.acceptance_config("examples.apps.purchase.acceptance.catalog")

scenarios(
    str(
        Path(__file__).resolve().parents[3]
        / "examples/apps/purchase/acceptance/features"
    )
)
