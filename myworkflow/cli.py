"""Command line entrypoint for framework development tools."""
import argparse
from myworkflow.build.cli import main as build_main


def main(argv=None):
    parser = argparse.ArgumentParser(prog='myworkflow')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('build', add_help=False, help='Validate declarations and generate target outputs')
    args, remaining = parser.parse_known_args(argv)
    return build_main(remaining)
