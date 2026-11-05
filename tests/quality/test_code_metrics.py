"""Optional statistics tools must count methods/closures and preserve failing tests."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytest.importorskip("coverage")
pytest.importorskip("radon")

from myworkflow.quality.code_metrics import complexity

ROOT = Path(__file__).resolve().parents[2]


def test_complexity_counts_functions_methods_and_closures_without_class_averages(
    tmp_path,
):
    package = tmp_path / "myworkflow"
    package.mkdir()
    (package / "sample.py").write_text("""def outer():
    def inner(flag):
        if flag:
            return 1
        return 0
    return inner

class Worker:
    def run(self, items):
        for item in items:
            if item:
                return item
""")
    result = complexity(tmp_path)
    assert sorted(b["complexity"] for b in result["functions"]) == [1, 2, 3]
    assert any("inner" in b["name"] for b in result["functions"])
    assert result["mean_complexity"] == 2
    assert result["files"][0]["functions"] == 3
    assert result["files"][0]["max_complexity"] == 3


@pytest.mark.parametrize(
    "startup_error", [False, True], ids=["failed-test", "invalid-pytest-option"]
)
def test_failed_tests_still_produce_reports_and_fail_the_metrics_command(
    tmp_path, startup_error
):
    failing = tmp_path / "test_failure.py"
    failing.write_text(
        'def test_failure():\n    assert False, "intentional failure for metrics reporting"\n'
    )
    output = tmp_path / "report"
    output.mkdir()
    # A previous successful JUnit result must never be reused after startup fails.
    (output / "pytest.xml").write_text(
        '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"/></testsuites>'
    )
    options = "--unknown-code-quality-option" if startup_error else str(failing)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "myworkflow.quality.code_metrics",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTEST_ADDOPTS": options},
        capture_output=True,
        text=True,
    )
    assert result.returncode == (4 if startup_error else 1), (
        result.stdout + result.stderr
    )
    report = json.loads((output / "metrics.json").read_text())
    assert report["pytest_exit_code"] == result.returncode
    if startup_error:
        assert report["tests"] is None
        assert "集計不能" in (output / "metrics.md").read_text()
    else:
        assert report["tests"]["failures"] == 1
        assert report["tests"]["passed"] == 0
    assert report["complexity"]["functions"]
    assert (output / "html/index.html").exists()
    assert (output / "coverage.xml").exists()
    assert (output / "metrics.md").exists()
    if "num_branches" not in report["coverage"]["totals"]:
        assert "分岐カバレッジ | 未計測" in (output / "metrics.md").read_text()
