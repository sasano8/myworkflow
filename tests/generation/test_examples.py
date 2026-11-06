"""Full generation uses the optional acceptance dependencies."""

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_generator_recovers_stale_interfaces_and_does_not_rewrite_oracles(tmp_path):
    for directory in ("myworkflow", "examples", "scripts"):
        shutil.copytree(
            ROOT / directory,
            tmp_path / directory,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    target = tmp_path / "examples/apps/purchase/interfaces.py"
    target.write_text(
        'raise RuntimeError("stale generated module must not be imported")\n'
    )
    oracle = tmp_path / "examples/apps/purchase/quality/business-expected.md"
    before = oracle.read_bytes()

    def run(*args):
        return subprocess.run(
            [sys.executable, "-m", "scripts.generate_docs", *args],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

    generated = run()
    assert generated.returncode == 0, generated.stderr
    assert "class PSubmitRequest" in target.read_text()
    assert oracle.read_bytes() == before
    checked = run("--check")
    assert checked.returncode == 0, checked.stderr
    data = tmp_path / "examples/apps/purchase/docs/data-definitions.md"
    data.write_text("manual drift\n")
    stale = run("--check")
    assert stale.returncode == 1
    assert data.read_text() == "manual drift\n"


def test_generated_documents_are_grouped_by_catalog_and_local_links_resolve():
    import re
    from urllib.parse import unquote, urlsplit
    from scripts.generate_docs import outputs

    generated = outputs()
    directories = {
        name.split("/docs/", 1)[0] + "/docs" for name in generated if "/docs/" in name
    }
    assert directories == {
        "examples/apps/purchase/docs",
        "examples/feature_demos/approval_values/docs",
        "examples/feature_demos/declarative_review/docs",
        "examples/apps/tickets/docs",
        "examples/apps/myworkflow_web/docs",
        "examples/feature_demos/prepared_approval/docs",
        "examples/feature_demos/manual_receipt/docs",
        "examples/feature_demos/product_catalogs/docs",
        "examples/feature_demos/cron_reporting/docs",
    }
    for directory in directories:
        assert directory + "/README.md" in generated
    for name, content in generated.items():
        if not name.endswith(".md"):
            continue
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            parsed = urlsplit(link)
            if parsed.scheme or not parsed.path:
                continue
            target = (ROOT / name).parent / unquote(parsed.path)
            assert target.exists(), f"{name}: broken relative link {link}"
            if target.name == "data-definitions.md" and parsed.fragment:
                assert f'id="{parsed.fragment}"' in target.read_text()
    assert not (ROOT / "examples/apps/purchase/requirements.md").exists()
    assert not (ROOT / "examples/apps/purchase/acceptance/business.md").exists()


def test_examples_separate_business_apps_from_feature_demos():
    import ast

    root = ROOT / "examples"
    assert {path.name for path in root.glob("*.py")} == {"__init__.py"}
    groups = {
        "apps": ("purchase", "tickets"),
        "feature_demos": (
            "approval_values",
            "declarative_review",
            "prepared_approval",
            "manual_receipt",
            "product_catalogs",
            "cron_reporting",
        ),
    }
    for group, names in groups.items():
        for name in names:
            directory = root / group / name
            assert (directory / "__init__.py").exists()
            assert (directory / "docs/README.md").exists()
            assert not (root / name).exists()
    # Business samples must remain runnable without importing a feature experiment.
    for path in (root / "apps").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            imports = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [name.name for name in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            assert all(
                not name.startswith("examples.feature_demos") for name in imports
            ), path
