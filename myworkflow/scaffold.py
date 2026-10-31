"""Generate initial code once, or refresh interfaces from code-owned contracts."""
import argparse
import importlib
import json
from pathlib import Path
from pprint import pformat

from myworkflow.executable import Program, interfaces_source, skeleton_source


def initialize(spec, directory):
    program = Program(spec)
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError(f"Refusing to overwrite existing work: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / '__init__.py').write_text('', encoding='utf-8')
    (directory / 'contract.py').write_text('"""Reviewed code-owned business contract."""\nSPEC = ' + pformat(spec, sort_dicts=False, width=110) + '\n', encoding='utf-8')
    (directory / 'interfaces.py').write_text(interfaces_source(program), encoding='utf-8')
    (directory / 'handlers.py').write_text(skeleton_source(program), encoding='utf-8')
    return program


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('reviewed_requirements')
    init.add_argument('directory')
    refresh = sub.add_parser('interfaces')
    refresh.add_argument('contract_module')
    refresh.add_argument('output')
    args = parser.parse_args()
    if args.command == 'init':
        initialize(json.loads(Path(args.reviewed_requirements).read_text(encoding='utf-8')), args.directory)
    else:
        program = Program(importlib.import_module(args.contract_module).SPEC)
        Path(args.output).write_text(interfaces_source(program), encoding='utf-8')


if __name__ == '__main__':
    main()
