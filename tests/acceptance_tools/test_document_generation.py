"""Full generation uses the optional acceptance dependencies."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_generator_recovers_stale_interfaces_and_does_not_rewrite_oracles(tmp_path):
    for directory in ('myworkflow', 'examples', 'scripts'):
        shutil.copytree(ROOT / directory, tmp_path / directory, ignore=shutil.ignore_patterns('__pycache__'))
    target = tmp_path / 'examples/purchase/interfaces.py'
    target.write_text('raise RuntimeError("stale generated module must not be imported")\n')
    oracle = tmp_path / 'examples/purchase/quality/business-expected.md'
    before = oracle.read_bytes()
    def run(*args):
        return subprocess.run([sys.executable, '-m', 'scripts.generate_docs', *args], cwd=tmp_path, capture_output=True, text=True)
    generated = run()
    assert generated.returncode == 0, generated.stderr
    assert 'class PSubmitRequest' in target.read_text()
    assert oracle.read_bytes() == before
    checked = run('--check')
    assert checked.returncode == 0, checked.stderr
    data = tmp_path / 'examples/purchase/data-definitions.md'
    data.write_text('manual drift\n')
    stale = run('--check')
    assert stale.returncode == 1
    assert data.read_text() == 'manual drift\n'
