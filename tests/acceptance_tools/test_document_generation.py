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
    data = tmp_path / 'examples/purchase/docs/data-definitions.md'
    data.write_text('manual drift\n')
    stale = run('--check')
    assert stale.returncode == 1
    assert data.read_text() == 'manual drift\n'


def test_generated_documents_are_grouped_by_catalog_and_local_links_resolve():
    import re
    from urllib.parse import unquote, urlsplit
    from scripts.generate_docs import outputs
    generated = outputs()
    directories = {str(Path(name).parent) for name in generated if name != 'examples/purchase/interfaces.py'}
    assert directories == {'examples/purchase/docs', 'examples/approval-values/docs',
                           'examples/declarative_review/docs', 'examples/tickets/docs'}
    for directory in directories:
        assert directory + '/README.md' in generated
    for name, content in generated.items():
        if not name.endswith('.md'):
            continue
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
            parsed = urlsplit(link)
            if parsed.scheme or not parsed.path:
                continue
            target = (ROOT / name).parent / unquote(parsed.path)
            assert target.exists(), f'{name}: broken relative link {link}'
            if target.name == 'data-definitions.md' and parsed.fragment:
                assert f'id="{parsed.fragment}"' in target.read_text()
    assert not (ROOT / 'examples/purchase/requirements.md').exists()
    assert not (ROOT / 'examples/purchase/acceptance/business.md').exists()
