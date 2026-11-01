"""Generation hooks preserve the index boundary and independent test oracles."""
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.generate_docs import refresh
from myworkflow.value_objects import render_data_definitions
from myworkflow import ContractCatalog, ValueModel, ValueObject
from pydantic import Field

ROOT = Path(__file__).resolve().parents[1]


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.STDOUT).decode()


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'user.email', 'test@example.invalid')
    git(tmp_path, 'config', 'user.name', 'Generation Test')
    (tmp_path / 'examples').mkdir()
    (tmp_path / 'examples/source.py').write_text('version = 1\n')
    (tmp_path / 'examples/generated.md').write_text('old\n')
    (tmp_path / 'notes.txt').write_text('unrelated\n')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'initial')
    return tmp_path


def test_hook_regenerates_and_stages_only_registered_outputs(repository):
    (repository / 'examples/source.py').write_text('version = 2\n')
    git(repository, 'add', 'examples/source.py')
    (repository / 'notes.txt').write_text('private unrelated edit\n')
    refresh({'examples/generated.md': 'new\n'}, root=repository, hook=True)
    assert git(repository, 'show', ':examples/generated.md') == 'new\n'
    assert git(repository, 'show', ':examples/source.py') == 'version = 2\n'
    assert git(repository, 'show', ':notes.txt') == 'unrelated\n'
    assert (repository / 'notes.txt').read_text() == 'private unrelated edit\n'


def test_hook_refuses_partial_source_changes_without_writing_or_staging(repository):
    (repository / 'examples/source.py').write_text('version = 2\n')
    git(repository, 'add', 'examples/source.py')
    (repository / 'examples/source.py').write_text('version = 3\n')
    with pytest.raises(ValueError, match='Stage generation inputs'):
        refresh({'examples/generated.md': 'new\n'}, root=repository, hook=True)
    assert git(repository, 'show', ':examples/source.py') == 'version = 2\n'
    assert (repository / 'examples/generated.md').read_text() == 'old\n'
    assert git(repository, 'show', ':examples/generated.md') == 'old\n'


def test_hook_refuses_untracked_source_and_preserves_unstaged_generated_edits(repository):
    source = repository / 'examples/new.py'
    source.write_text('untracked = True\n')
    with pytest.raises(ValueError, match='Stage generation inputs'):
        refresh({'examples/generated.md': 'new\n'}, root=repository, hook=True)
    source.unlink()
    (repository / 'examples/generated.md').write_text('manual edit\n')
    with pytest.raises(ValueError, match='would be overwritten'):
        refresh({'examples/generated.md': 'new\n'}, root=repository, hook=True)
    assert (repository / 'examples/generated.md').read_text() == 'manual edit\n'
    assert git(repository, 'show', ':examples/generated.md') == 'old\n'


def test_hook_accepts_already_generated_outputs_and_check_never_writes(repository):
    (repository / 'examples/generated.md').write_text('new\n')
    refresh({'examples/generated.md': 'new\n'}, root=repository, hook=True)
    assert git(repository, 'show', ':examples/generated.md') == 'new\n'
    with pytest.raises(ValueError, match='stale'):
        refresh({'examples/generated.md': 'different\n'}, root=repository, check=True)
    assert (repository / 'examples/generated.md').read_text() == 'new\n'


def test_output_path_cannot_escape_repository(repository):
    with pytest.raises(ValueError, match='stay inside'):
        refresh({'../escape.md': 'bad'}, root=repository)
    assert not (repository.parent / 'escape.md').exists()


def test_installer_preserves_existing_hooks_and_activates_tracked_hook(repository):
    shutil.copytree(ROOT / '.githooks', repository / '.githooks')
    script = ROOT / 'scripts/install-hooks.sh'
    old = repository / '.git/hooks/pre-commit'
    old.write_text('#!/bin/sh\nexit 0\n')
    old.chmod(0o755)
    refused = subprocess.run(['sh', str(script)], cwd=repository, capture_output=True, text=True)
    assert refused.returncode == 1
    assert old.read_text() == '#!/bin/sh\nexit 0\n'
    old.unlink()
    subprocess.run(['sh', str(script)], cwd=repository, check=True, capture_output=True)
    assert git(repository, 'config', '--get', 'core.hooksPath').strip() == '.githooks'
    git(repository, 'config', 'core.hooksPath', 'custom-hooks')
    refused = subprocess.run(['sh', str(script)], cwd=repository, capture_output=True, text=True)
    assert refused.returncode == 1
    assert git(repository, 'config', '--get', 'core.hooksPath').strip() == 'custom-hooks'


def test_compact_tables_cover_nested_arrays_nullable_fields_and_enum():
    from typing import Literal
    class Line(ValueModel):
        quantity: int = Field(ge=1, examples=[2])
    class Order(ValueModel):
        lines: list[Line] = Field(min_length=1)
        memo: str | None = None
        choice: Literal['A', 'B'] = 'A'
    text = render_data_definitions(ContractCatalog((), (), (), value_objects=(ValueObject('vo.order', '注文', Order),)))
    assert 'lines[].quantity' in text
    assert '親あり時に必須' in text
    assert '1以上' in text
    assert '文字列 / null' in text
    assert '選択肢：A、B' in text
    assert '```' not in text



def test_union_constraints_remain_alternatives_in_compact_table():
    from typing import Annotated
    class Choice(ValueModel):
        value: Annotated[str, Field(min_length=2)] | Annotated[int, Field(ge=10)]
    text = render_data_definitions(ContractCatalog((), (), (), value_objects=(ValueObject('vo.choice', '選択値', Choice),)))
    assert 'いずれか：文字列（文字数の下限：2）／整数（10以上）' in text


def test_recursive_schema_has_bounded_summary():
    class Node(ValueModel):
        child: 'Node | None' = None
    Node.model_rebuild()
    text = render_data_definitions(ContractCatalog((), (), (), value_objects=(ValueObject('vo.node', '階層', Node),)))
    assert 'child' in text
    assert len(text.splitlines()) < 50
    assert '```' not in text



def test_value_document_has_one_horizontal_row_per_item():
    from examples.purchase.contract import program
    text = render_data_definitions(program.model)
    rows = [line for line in text.splitlines() if line.startswith('| ')]
    assert len(rows) == 5  # One header, one separator and three actual items.
    assert '| 項目 | 内容 |' not in text
    assert '\n## ' not in text
    assert '| 購買申請ID | 文字列 | 必須 |' in rows[2]
    assert '| 取引先名 | 文字列 | 必須 |' in rows[3]
    assert '| 購買申請金額 | 整数 | 必須 |' in rows[4]
    assert '空文字・空白だけの取引先名を拒否する' in rows[3]
    assert '0より大きい' in rows[4]
    assert '<a id="vo.purchase.amount"></a>' in rows[4]
