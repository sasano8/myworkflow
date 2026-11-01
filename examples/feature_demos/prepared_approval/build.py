"""Build the artifact preparation and commit example."""
from examples.feature_demos.prepared_approval.application import compiled, registry
from myworkflow.build import BuildConfig

BUILD = BuildConfig(compiled, registry)
