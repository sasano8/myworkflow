"""Build configuration; canonical business declarations live only in contract.py."""

from myworkflow.build import BuildConfig
from examples.apps.purchase.contract import compiled
from examples.apps.purchase.handlers import registry

BUILD = BuildConfig(compiled, registry)
