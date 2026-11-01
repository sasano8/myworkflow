"""Build the guarded approval with independent data definitions."""
from examples.approval_values.application import compiled, registry
from myworkflow.build import BuildConfig

BUILD = BuildConfig(compiled, registry)
