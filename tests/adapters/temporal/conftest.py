"""Temporal tests run only when their optional prerequisites are configured."""

import importlib.util
import os

collect_ignore = []
if importlib.util.find_spec("temporalio") is None:
    collect_ignore += ["test_pipeline_result.py", "test_purchase.py"]
elif not os.environ.get("TEMPORAL_CLI_PATH"):
    collect_ignore += ["test_purchase.py"]
