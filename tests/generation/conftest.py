"""Complete example generation requires the acceptance extras."""
import importlib.util

collect_ignore = ['test_examples.py'] if importlib.util.find_spec('pytest_bdd') is None else []
