"""Business acceptance scenarios for the purchase sample."""
from pathlib import Path
from pytest_bdd import scenarios

scenarios(str(Path(__file__).resolve().parents[2] / 'examples/purchase/acceptance/features'))
