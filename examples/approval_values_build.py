"""Build the guarded approval with independent data definitions."""
from examples.guarded_approval import compiled, registry
from myworkflow.build import BuildConfig

BUILD = BuildConfig(compiled, registry)
