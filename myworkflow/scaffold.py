"""Generate initial code once, or refresh interfaces from code-owned contracts."""
import argparse
import importlib
import json
from pathlib import Path
from pprint import pformat

from myworkflow.executable import Program, interfaces_source, skeleton_source
from myworkflow.generation import write_outputs


def initialize(spec, directory):
    program = Program(spec)
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError(f"Refusing to overwrite existing work: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    write_outputs({directory / '__init__.py': '',
        directory / 'contract.py': '"""Reviewed code-owned business contract."""\nSPEC = ' + pformat(spec, sort_dicts=False, width=110) + '\n',
        directory / 'interfaces.py': interfaces_source(program),
        directory / 'handlers.py': skeleton_source(program)})
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
        module = importlib.import_module(args.contract_module)
        program = module.program if hasattr(module, 'program') else Program(module.SPEC)
        source = Path(module.__file__)
        write_outputs({Path(args.output): interfaces_source(program)}, protected=(source, source.with_name('handlers.py')))


if __name__ == '__main__':
    main()
