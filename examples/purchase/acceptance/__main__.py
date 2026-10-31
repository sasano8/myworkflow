"""Compatibility command for purchase documents; the implementation is generic."""
from examples.purchase.acceptance.catalog import CONFIG
from myworkflow.acceptance.cli import main

if __name__ == '__main__':
    main(CONFIG, application="examples.purchase.acceptance.catalog")
