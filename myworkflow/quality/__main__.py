import argparse
import json
from pathlib import Path

from myworkflow.generation.files import write_outputs
from myworkflow.quality.runner import run_case
from myworkflow._internal.jsonio import read_json
from myworkflow.quality.rendering import render_quality


def main():
    parser = argparse.ArgumentParser(
        description="Generate interfaces and measure requirement round-trip quality"
    )
    parser.add_argument("--case", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case_path = Path(args.case).resolve()
    output = Path(args.output).resolve()
    if output == case_path or output in case_path.parents:
        raise ValueError("Quality artifacts must not overwrite the input directory")
    protected = [case_path]
    try:
        case = read_json(case_path.read_text(encoding="utf-8"))
        protected += [
            (case_path.parent / case[k]).resolve()
            for k in (
                "source",
                "business_input",
                "expected_markdown",
                "coverage",
                "sample_conversion",
            )
        ]
    except ValueError, KeyError, TypeError, OSError:
        pass
    report, artifacts = run_case(case_path)
    artifacts["quality.json"] = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    artifacts["quality.md"] = render_quality(report)
    write_outputs(
        {output / name: text for name, text in artifacts.items()}, protected=protected
    )
    print(
        f"{report.get('case_id', 'quality')}: {'PASS' if report['passed'] else 'FAIL'}; {output / 'quality.md'}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
