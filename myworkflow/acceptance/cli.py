"""Application-configured generation; handwritten inputs are never outputs."""
import argparse
import json
from pathlib import Path
from myworkflow.acceptance.rendering import render_business, render_cases
from myworkflow.acceptance.reports import render_report, validate_report
from myworkflow.generation.files import write_outputs


def main(config, argv=None, *, application=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    docs = sub.add_parser('docs')
    docs.add_argument('--check', action='store_true')
    report = sub.add_parser('report')
    report.add_argument('results')
    args = parser.parse_args(argv)
    cases = config.cases()
    if args.command == 'docs':
        if config.output_directory is None:
            raise ValueError('Configure an output_directory for document generation')
        outputs = {config.output_directory / 'acceptance.md': render_cases(cases, config.definitions, options=config.documents),
                   config.output_directory / 'business.md': render_business(config.program, config.registry, cases, options=config.documents)}
        write_outputs(outputs, check=args.check, protected=config.features)
    else:
        payload = json.loads(Path(args.results).read_text(encoding='utf-8'))
        validate_report(payload)
        known = {c.id for c in cases}
        for entry in payload['cases']:
            if entry['case_id'] not in known and (application is None or entry.get('application') in (None, application)):
                raise ValueError(f'Unknown case in application report: {entry["case_id"]}')
        payload = {**payload, 'cases': [r for r in payload['cases'] if r['case_id'] in known]}
        print(render_report(payload, cases, config.contract_hash(), config.implementation_hash(), options=config.documents), end='')
