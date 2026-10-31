from pathlib import Path

from examples.purchase.contract import SPEC
from examples.purchase.handlers import registry
from examples.purchase.acceptance.steps import steps
from myworkflow.acceptance import load_cases
from myworkflow.executable import Program

DIRECTORY = Path(__file__).resolve().parent
program = Program(SPEC)


def cases():
    return load_cases(list((DIRECTORY / 'features').glob('*.feature')), program, steps)


def implementation_hash():
    """Invalidate old results if business code, adapters or the test harness change."""
    import hashlib
    root = DIRECTORY.parents[2]
    paths = [DIRECTORY / 'steps.py', DIRECTORY / 'world.py', DIRECTORY / 'catalog.py', DIRECTORY / '__main__.py',
             root / 'examples/purchase/scheduling.py', root / 'examples/purchase/handlers.py',
             root / 'examples/purchase/services.py', root / 'examples/purchase/interfaces.py',
             root / 'examples/purchase/temporal_workflow.py', root / 'myworkflow/executable.py',
             root / 'myworkflow/acceptance.py', root / 'myworkflow/temporal.py', root / 'myworkflow/__init__.py',
             root / 'tests/conftest.py', root / 'tests/acceptance/conftest.py', root / 'tests/acceptance/test_purchase.py']
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()
