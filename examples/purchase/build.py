"""Build configuration; canonical business declarations live only in contract.py."""
from myworkflow.build import BuildConfig
from examples.purchase.contract import compiled
from examples.purchase.handlers import registry

BUILD = BuildConfig(compiled, registry)
