"""No application imports: core pytest works without BDD dependencies."""

import pytest

pytest.register_assert_rewrite(
    "examples.apps.purchase.acceptance.steps", "examples.apps.tickets.acceptance.steps"
)

pytest_plugins = ["myworkflow.acceptance.pytest_plugin"]
