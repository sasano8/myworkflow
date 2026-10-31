import importlib
import sys
from myworkflow.acceptance.cli import main

if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] != '--config':
        raise SystemExit('Usage: python -m myworkflow.acceptance --config APPLICATION_MODULE docs|report ...')
    main(importlib.import_module(sys.argv[2]).CONFIG, sys.argv[3:], application=sys.argv[2])
