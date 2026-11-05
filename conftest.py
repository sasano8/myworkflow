"""Test settings shared by the core and optional integration suites."""

import pytest


@pytest.hookimpl(trylast=True)
def pytest_addoption(parser, pluginmanager):
    if pluginmanager.hasplugin("asyncio"):
        # Set the plugin's default without requiring it in the core environment.
        parser.addini(
            "asyncio_default_fixture_loop_scope",
            "Default event loop scope for async fixtures",
            type="string",
            default="function",
        )
