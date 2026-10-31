"""Generate specifications or render a separate execution report."""
import argparse
import hashlib
import json
from pathlib import Path

from examples.purchase.acceptance.catalog import DIRECTORY, cases, implementation_hash, program, registry, steps
from myworkflow.acceptance import render_business, render_cases, render_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    docs = sub.add_parser('docs')
    docs.add_argument('--check', action='store_true')
    report = sub.add_parser('report')
    report.add_argument('results')
    args = parser.parse_args()
    catalog = cases()
    if args.command == 'docs':
        outputs = {'acceptance.md': render_cases(catalog, steps), 'business.md': render_business(program, registry, catalog)}
        for name, text in outputs.items():
            path = DIRECTORY / name
            if args.check:
                if not path.exists() or path.read_text(encoding='utf-8') != text:
                    raise SystemExit(f'Generated document is stale: {path}')
            else:
                path.write_text(text, encoding='utf-8')
    else:
        payload = json.loads(Path(args.results).read_text(encoding='utf-8'))
        contract_hash = hashlib.sha256(json.dumps(program.spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        print(render_report(payload, catalog, contract_hash, implementation_hash()), end='')


if __name__ == '__main__':
    main()
