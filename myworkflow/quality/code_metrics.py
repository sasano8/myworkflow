"""Opt-in repository statistics: coverage.py tests and Radon source analysis."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

from myworkflow._internal.fingerprints import tree_fingerprint
from myworkflow._internal.markdown import escape


def complexity(root):
    from radon.complexity import add_inner_blocks, cc_rank, cc_visit
    from radon.metrics import mi_rank, mi_visit
    from radon.raw import analyze
    from radon.visitors import Function

    files, functions = [], []
    for path in sorted((root / "myworkflow").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        name = path.relative_to(root).as_posix()
        blocks = [
            b for b in add_inner_blocks(cc_visit(source)) if isinstance(b, Function)
        ]
        functions.extend(
            {
                "file": name,
                "name": b.fullname,
                "line": b.lineno,
                "complexity": b.complexity,
                "rank": cc_rank(b.complexity),
            }
            for b in blocks
        )
        raw, mi = analyze(source), mi_visit(source, multi=True)
        files.append(
            {
                "file": name,
                "loc": raw.loc,
                "sloc": raw.sloc,
                "functions": len(blocks),
                "max_complexity": max((b.complexity for b in blocks), default=0),
                "maintainability_index": mi,
                "maintainability_rank": mi_rank(mi),
            }
        )
    functions.sort(key=lambda b: (-b["complexity"], b["file"], b["line"], b["name"]))
    return {
        "files": files,
        "functions": functions,
        "rank_counts": dict(sorted(Counter(b["rank"] for b in functions).items())),
        "mean_complexity": sum(b["complexity"] for b in functions) / len(functions)
        if functions
        else 0,
    }


def render(report):
    totals = report["coverage"]["totals"]
    percent = lambda covered, total: f"{100 * covered / total:.2f}%" if total else "—"
    analysis = report["complexity"]
    tests = report["tests"]
    branch_measured = "num_branches" in totals
    branch = (
        f"{percent(totals['covered_branches'], totals['num_branches'])} ({totals['covered_branches']}/{totals['num_branches']})"
        if branch_measured
        else "未計測"
    )
    test_summary = (
        f"成功 {tests['passed']}、失敗 {tests['failures']}、エラー {tests['errors']}、スキップ {tests['skipped']}"
        if tests is not None
        else "JUnit結果なし（集計不能）"
    )
    lines = [
        "# コード品質の計測結果",
        "",
        f"計測：{report['measured_at']}。対象：`myworkflow/`（サンプル・テストを除く）。",
        "",
        f"ソースSHA256：`{report['source_sha256']}`。基点コミット：`{report['commit']}`。未コミット変更：{report['dirty']}。",
        "",
        f"Python {report['python']} / coverage.py {report['tools']['coverage']} / Radon {report['tools']['radon']}。",
        "",
        f"テスト：{test_summary}。終了コード：{report['pytest_exit_code']}。",
        "",
        "| 指標 | 値 |",
        "| --- | --- |",
        f"| 行カバレッジ | {percent(totals['covered_lines'], totals['num_statements'])} ({totals['covered_lines']}/{totals['num_statements']}) |",
        f"| 分岐カバレッジ | {branch} |",
        f"| 関数・メソッド数（ネストを含む） | {len(analysis['functions'])} |",
        f"| 平均循環的複雑度 | {analysis['mean_complexity']:.2f} |",
        f"| 複雑度ランク別件数 | {escape(analysis['rank_counts'])} |",
        "",
        "## パッケージ別カバレッジ",
        "",
        "| パッケージ | 行 | 分岐 |",
        "| --- | --- | --- |",
    ]
    packages = {}
    for name, data in report["coverage"]["files"].items():
        parts = Path(name).parts
        package = parts[1] if len(parts) > 2 else "(root)"
        summary = packages.setdefault(package, Counter())
        summary.update(
            {
                key: data["summary"].get(key, 0)
                for key in (
                    "covered_lines",
                    "num_statements",
                    "covered_branches",
                    "num_branches",
                )
            }
        )
    for name, summary in sorted(packages.items()):
        lines.append(
            f"| {escape(name)} | {percent(summary['covered_lines'], summary['num_statements'])} | {percent(summary['covered_branches'], summary['num_branches']) if branch_measured else '未計測'} |"
        )
    lines += [
        "",
        "## 複雑度の高い処理（上位15件）",
        "",
        "| 処理 | 行 | CC | ランク |",
        "| --- | --- | --- | --- |",
    ]
    for block in analysis["functions"][:15]:
        lines.append(
            f"| {escape(block['file'] + ':' + block['name'])} | {block['line']} | {block['complexity']} | {block['rank']} |"
        )
    lines += [
        "",
        "詳細な関数別CC・ファイル別LOC/SLOC・保守性指標はmetrics.json、未実行行はcoverage.json・HTMLを参照。",
        "CCは分岐経路数の目安、MIは静的な保守性指標です。数値だけで品質や業務条件の網羅を保証しません。",
        "サブプロセスも計測します。利用した任意依存・Temporal設定はmetrics.jsonに記録し、構成の違う結果を単純比較しません。",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/code-quality"))
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Also write the summary to a reviewed Markdown file",
    )
    args = parser.parse_args(argv)
    root = Path.cwd()
    if not (root / "pyproject.toml").is_file() or not (root / "myworkflow").is_dir():
        parser.error("Run from the repository root")
    if args.snapshot and args.snapshot.suffix != ".md":
        parser.error("--snapshot must be a Markdown file")
    try:
        tools = {name: version(name) for name in ("coverage", "radon", "pytest")}
    except PackageNotFoundError:
        parser.error(
            "Install the quality tools: python -m pip install -e '.[test,acceptance,quality]'"
        )
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name in ("pytest.xml", "metrics.json", "metrics.md"):
        (output / name).unlink(missing_ok=True)
    env = {
        **os.environ,
        "COVERAGE_FILE": str(output / ".coverage"),
        "COVERAGE_RCFILE": str(root / "pyproject.toml"),
    }

    def coverage(*arguments):
        return [sys.executable, "-m", "coverage", *arguments]

    subprocess.run(coverage("erase"), env=env, check=True)
    command = coverage(
        "run", "-m", "pytest", "-q", f"--junitxml={output / 'pytest.xml'}"
    )
    # Preserve test failures while still producing diagnostic coverage and complexity.
    result = subprocess.run(command, env=env)
    subprocess.run(coverage("combine"), env=env, check=True)
    for format, target in (
        ("json", "coverage.json"),
        ("xml", "coverage.xml"),
        ("html", "html"),
    ):
        subprocess.run(
            coverage(format, "-d" if format == "html" else "-o", str(output / target)),
            env=env,
            check=True,
        )
    tests = None
    if (output / "pytest.xml").exists():
        tests = Counter({key: 0 for key in ("tests", "failures", "errors", "skipped")})
        for suite in ET.parse(output / "pytest.xml").getroot().iter("testsuite"):
            tests.update({key: int(suite.get(key, 0)) for key in tests})
        tests["passed"] = (
            tests["tests"] - tests["failures"] - tests["errors"] - tests["skipped"]
        )
    git = lambda *args: subprocess.check_output(["git", *args], text=True).strip()
    optional = {}
    for name in ("pytest-bdd", "temporalio"):
        try:
            optional[name] = version(name)
        except PackageNotFoundError:
            optional[name] = None
    report = {
        "schema_version": 1,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "source_sha256": tree_fingerprint(root, [root / "myworkflow"]),
        "python": platform.python_version(),
        "tools": tools,
        "optional_dependencies": optional,
        "temporal": {
            name: os.environ.get(name)
            for name in ("RUN_TEMPORAL_ACCEPTANCE", "TEMPORAL_CLI_PATH")
        },
        "test_command": command,
        "pytest_exit_code": result.returncode,
        "tests": dict(tests) if tests is not None else None,
        "coverage": json.loads((output / "coverage.json").read_text()),
        "complexity": complexity(root),
    }
    (output / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = render(report)
    (output / "metrics.md").write_text(summary, encoding="utf-8")
    if args.snapshot:
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot.write_text(summary, encoding="utf-8")
    print(f"Code metrics: {output / 'metrics.md'}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
