"""Enforce dependency direction and the lightweight contract/public API boundary."""

import ast
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("layer", "forbidden"),
    [
        (
            "contracts",
            {
                "compiler",
                "runtime",
                "storage",
                "adapters",
                "generation",
                "build",
                "acceptance",
                "quality",
            },
        ),
        (
            "compiler",
            {
                "runtime",
                "storage",
                "adapters",
                "generation",
                "build",
                "acceptance",
                "quality",
            },
        ),
        (
            "storage",
            {
                "compiler",
                "runtime",
                "adapters",
                "generation",
                "build",
                "acceptance",
                "quality",
            },
        ),
        ("runtime", {"adapters", "generation", "build", "acceptance", "quality"}),
        ("generation", {"runtime", "adapters", "build", "acceptance", "quality"}),
        (
            "_internal",
            {
                "contracts",
                "compiler",
                "runtime",
                "storage",
                "adapters",
                "generation",
                "build",
                "acceptance",
                "quality",
            },
        ),
    ],
)
def test_inner_layers_do_not_import_outer_layers(layer, forbidden):
    for path in (ROOT / "myworkflow" / layer).rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [name.name for name in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            for name in names:
                if name.startswith("myworkflow."):
                    assert name.split(".")[1] not in forbidden, f"{path}: {name}"
                assert name not in ("myworkflow", "myworkflow.executable"), (
                    f"{path}: use a direct inner-layer import"
                )


def test_contract_import_does_not_load_execution_or_generation():
    code = """import sys
from myworkflow import ContractCatalog, ValueModel, PipelineResult
assert ContractCatalog.__name__ == 'ContractCatalog'
assert not any(name.split('.')[1] in {'runtime', 'compiler', 'generation', 'adapters', 'quality', 'acceptance', 'build'}
               for name in sys.modules if name.startswith('myworkflow.'))
"""
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)


def test_default_collection_includes_build_tests():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--ignore=tests/apps",
            "--ignore=tests/acceptance",
            "--ignore=tests/architecture",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (
        "tests/build/test_build.py::test_temporal_build_validates_code_without_generating_another_runtime"
        in result.stdout
    )
    assert (
        "tests/build/test_value_outputs.py::test_build_includes_separate_data_files_and_detects_constraint_drift"
        in result.stdout
    )


def test_source_and_test_build_packages_are_not_gitignored():
    result = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "check-ignore",
            "--no-index",
            "myworkflow/build/__init__.py",
            "myworkflow/build/__main__.py",
            "tests/build/test_value_outputs.py",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout + result.stderr
