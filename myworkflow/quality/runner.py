"""Source → reviewed business format → generated code → independently checked output."""

from myworkflow.generation.documents import document_program
from contextlib import contextmanager
from difflib import SequenceMatcher
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

from myworkflow.compiler.program import Program
from myworkflow._internal.fingerprints import tree_fingerprint
from myworkflow._internal.jsonio import read_json
from myworkflow.generation.scaffold import initialize
from myworkflow.generation.business import business_to_spec, export_business
from myworkflow.quality.interfaces import check_interfaces
from myworkflow.quality.metrics import compare, source_coverage


@contextmanager
def emitted_module(path):
    identity = "_myworkflow_quality_" + uuid4().hex
    spec = importlib.util.spec_from_file_location(identity, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[identity] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(identity, None)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_case(case_path, *, converter=None, generator=initialize):
    case_path = Path(case_path).resolve()
    report = {
        "schema_version": 1,
        "passed": False,
        "metrics": {},
        "stages": {},
        "failures": [],
        "converter": {
            "name": "reviewed-sample"
            if converter is None
            else getattr(converter, "__module__", type(converter).__module__)
            + "."
            + getattr(converter, "__qualname__", type(converter).__qualname__),
            "mode": "reviewed-fixture"
            if converter is None
            else "source-only-candidate",
        },
        "python": platform.python_version(),
    }
    artifacts = {}
    stage = "load"
    try:
        case = read_json(case_path.read_text(encoding="utf-8"))
        if (
            type(case.get("schema_version")) is not int
            or case.get("schema_version") != 1
        ):
            raise ValueError("Unsupported quality-case schema")
        report["case_id"] = case["id"]

        def read(key):
            return (case_path.parent / case[key]).read_text(encoding="utf-8")

        source = read("source")
        expected = read_json(read("business_input"))
        corpus = read_json(read("coverage"))
        expected_markdown = read("expected_markdown")
        package = Path(__file__).resolve().parents[1]
        artifacts["business-input.json"] = (
            json.dumps(expected, ensure_ascii=False, indent=2) + "\n"
        )
        report["provenance"] = {
            "case_sha256": sha(case_path.read_text(encoding="utf-8")),
            "framework_sha256": tree_fingerprint(package.parent, [package]),
            "source_sha256": sha(source),
            "business_input_sha256": sha(read("business_input")),
            "inventory_sha256": sha(read("coverage")),
            "expected_markdown_sha256": sha(expected_markdown),
        }
        git = subprocess.run(
            ["git", "-C", str(case_path.parent), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        report["provenance"]["commit"] = (
            git.stdout.strip() if git.returncode == 0 else None
        )
        git = subprocess.run(
            ["git", "-C", str(case_path.parent), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        report["provenance"]["working_tree_dirty"] = (
            bool(git.stdout.strip()) if git.returncode == 0 else None
        )
        # Validate the independent oracle and source inventory, without re-creating them.
        Program(business_to_spec(expected))
        source_coverage(source, corpus, expected)
        report["stages"][stage] = "passed"
        stage = "convert"
        # External/AI candidates receive only the source, never the scoring oracle.
        converted = (
            read_json(read("sample_conversion"))
            if converter is None
            else converter(source)
        )
        if converter is None:
            report["provenance"]["conversion_fixture_sha256"] = sha(
                read("sample_conversion")
            )
        artifacts["business-converted.json"] = (
            json.dumps(converted, ensure_ascii=False, indent=2) + "\n"
        )
        metrics = report["metrics"]
        metrics["conversion"] = compare(expected, converted)
        spec = business_to_spec(converted)
        Program(spec)
        report["stages"][stage] = "passed"
        stage = "generate"
        with TemporaryDirectory(prefix="myworkflow-quality-") as temporary:
            directory = Path(temporary) / "code"
            generator(spec, directory)
            for name in ("contract.py", "interfaces.py", "handlers.py"):
                artifacts["code/" + name] = (directory / name).read_text(
                    encoding="utf-8"
                )
            report["provenance"]["generated_sha256"] = {
                name: sha(text) for name, text in artifacts.items()
            }
            report["stages"][stage] = "passed"
            stage = "export"
            with (
                emitted_module(directory / "contract.py") as contract,
                emitted_module(directory / "interfaces.py") as interfaces,
                emitted_module(directory / "handlers.py") as handlers,
            ):
                actual_program = Program(contract.SPEC)
                actual = export_business(actual_program)
                metrics["interfaces"] = check_interfaces(expected, interfaces)
                wanted_handlers = {
                    s for s, v in expected["steps"].items() if v["kind"] == "action"
                }
                wanted_handlers |= {
                    v["compensate"]
                    for v in expected["steps"].values()
                    if v.get("compensate")
                }
                actual_handlers = set(handlers.registry.handlers)
                metrics["skeleton"] = {
                    "missing": sorted(wanted_handlers - actual_handlers),
                    "unexpected": sorted(actual_handlers - wanted_handlers),
                    "passed": wanted_handlers == actual_handlers,
                }
                markdown = document_program(actual_program)
            report["stages"][stage] = "passed"
        stage = "compare"
        metrics["roundtrip"] = compare(expected, actual)
        metrics["converted_to_code"] = compare(converted, actual)
        metrics["source"] = source_coverage(source, corpus, actual)
        metrics["markdown"] = {
            "exact_match": markdown == expected_markdown,
            "text_similarity": SequenceMatcher(
                None, expected_markdown, markdown, autojunk=False
            ).ratio(),
        }
        artifacts.update(
            {
                "business-output.json": json.dumps(actual, ensure_ascii=False, indent=2)
                + "\n",
                "business-output.md": markdown,
            }
        )
        thresholds = case["thresholds"]
        required = (
            "conversion_recall",
            "conversion_precision",
            "roundtrip_recall",
            "roundtrip_precision",
            "documented_coverage",
            "structured_coverage",
            "source_inventory_coverage",
        )
        if set(thresholds) != set(required) or any(
            type(v) not in (int, float) or not 0 <= v <= 1 for v in thresholds.values()
        ):
            raise ValueError("Quality gates require all bounded numeric thresholds")
        values = {
            "conversion_recall": metrics["conversion"]["recall"],
            "conversion_precision": metrics["conversion"]["precision"],
            "roundtrip_recall": metrics["roundtrip"]["recall"],
            "roundtrip_precision": metrics["roundtrip"]["precision"],
            **{
                k: metrics["source"][k]
                for k in (
                    "documented_coverage",
                    "structured_coverage",
                    "source_inventory_coverage",
                )
            },
        }
        report["thresholds"] = thresholds
        report["observed"] = values
        for name, minimum in thresholds.items():
            if values[name] < minimum:
                report["failures"].append(f"{name}: {values[name]:.6f} < {minimum:.6f}")
        if not metrics["converted_to_code"]["exact_match"]:
            report["failures"].append(
                "Generated code did not preserve the converted business document"
            )
        if not metrics["interfaces"]["passed"]:
            report["failures"].append(
                "Generated interface declarations do not match the independent input"
            )
        if not metrics["skeleton"]["passed"]:
            report["failures"].append(
                "Generated handler skeleton connections do not match the input"
            )
        if metrics["source"]["new_gaps"]:
            report["failures"].append(
                "New unrepresented requirements: "
                + ", ".join(metrics["source"]["new_gaps"])
            )
        if not metrics["markdown"]["exact_match"]:
            report["failures"].append(
                "Generated business Markdown differs from the reviewed input snapshot"
            )
        report["stages"][stage] = "passed" if not report["failures"] else "failed"
        report["passed"] = not report["failures"]
        report["judgment"] = (
            (
                "meets-reviewed-baseline-with-known-gaps"
                if metrics["source"]["gaps"]
                else "meets-reviewed-baseline"
            )
            if report["passed"]
            else "failed"
        )
    except Exception as exc:
        report["stages"][stage] = "failed"
        report["failures"].append(f"{stage}: {type(exc).__name__}: {exc}")
    for name in ("load", "convert", "generate", "export", "compare"):
        report["stages"].setdefault(name, "not-run")
    return report, artifacts
