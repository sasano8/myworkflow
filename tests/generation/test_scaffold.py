"""Scaffold and generated interfaces preserve handwritten source."""
import json
from pathlib import Path
import pytest
from examples.apps.purchase.contract import program
from examples.apps.purchase.handlers import registry
from myworkflow.executable import Context, Program, interfaces_source
from myworkflow.generation.documents import document_program
from myworkflow.generation.scaffold import initialize

ROOT = Path(__file__).resolve().parents[2]

class TestScaffold:
    @pytest.fixture(autouse=True)
    def prepare(self, tmp_path):
        self.tmp_path = tmp_path
        self.program = program

    def test_source_snapshots_match(self):
        assert interfaces_source(self.program) == (ROOT / 'examples/apps/purchase/interfaces.py').read_text()
        assert document_program(self.program, registry, details_link='../../../../docs/execution-design.md') == (ROOT / 'examples/apps/purchase/docs/requirements.md').read_text()


    def test_initial_generation_and_unimplemented_skeleton(self):
        initial = json.loads((ROOT / 'docs/requirements/purchase-initial.json').read_text())
        target = self.tmp_path / 'generated'
        initialize(initial, target)
        namespace = {}
        exec((target / 'handlers.py').read_text(), namespace)
        with pytest.raises(NotImplementedError):
            namespace['registry'].handlers['s.submit'](Context({}, None, 'id', 'actor', []))
        with pytest.raises(FileExistsError):
            initialize(initial, target)
        assert (target / 'interfaces.py').read_text() == interfaces_source(Program(initial))
        namespace = {}
        exec((target / 'contract.py').read_text(), namespace)
        assert namespace['SPEC'] == initial


    def test_interface_refresh_preserves_handwritten_implementation(self):
        import subprocess
        import sys
        target = self.tmp_path / 'generated'
        initial = json.loads((ROOT / 'docs/requirements/purchase-initial.json').read_text())
        initialize(initial, target)
        implementation = target / 'handlers.py'
        implementation.write_text('# handwritten implementation must survive\n')
        before = implementation.read_bytes()
        subprocess.run([sys.executable, '-m', 'myworkflow.generation.scaffold', 'interfaces',
                        'examples.apps.purchase.contract', str(target / 'interfaces.py')], cwd=ROOT, check=True)
        assert implementation.read_bytes() == before
        assert (target / 'interfaces.py').read_text() == interfaces_source(self.program)
