"""Build CLI. The typed compiler is in build/compiler.py; no deployment is performed."""

import argparse
import importlib
import inspect
from pathlib import Path
import sys

from myworkflow.build.compiler import BuildConfig, BuildError, build, compile_outputs
from myworkflow.contracts.errors import ContractError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", required=True, help="Python module exposing BUILD: BuildConfig"
    )
    parser.add_argument("--target", choices=("temporal", "kestra"), required=True)
    parser.add_argument(
        "--workflow",
        action="append",
        default=[],
        help="Explicit subset of workflow IDs",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--check", action="store_true", help="Fail on stale outputs; do not write"
    )
    args = parser.parse_args(argv)
    try:
        # Installed console scripts must discover the application in the working directory too.
        project = str(Path.cwd())
        if project not in sys.path:
            sys.path.insert(0, project)
        module = importlib.import_module(args.config)
        config = getattr(module, "BUILD", None)
        protected = (
            (
                module.__file__,
                *(inspect.getsourcefile(c) for c in config.compiled.declarations),
            )
            if isinstance(config, BuildConfig)
            else ()
        )
        build(
            config,
            args.output,
            target=args.target,
            workflows=args.workflow,
            check=args.check,
            protected=tuple(path for path in protected if path),
        )
    except (BuildError, ContractError, ValueError, OSError, ImportError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"{args.target}: {'checked' if args.check else 'built'} {args.output}"
        + (" (preview; not deployable)" if args.target == "kestra" else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
