"""Run the example catalog."""
from pathlib import Path
from tempfile import TemporaryDirectory
from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.executable import Principal
from examples.prepared_approval.application import engine, reviewer, seed


with TemporaryDirectory() as temporary:
    coordinator = TemporaryArtifactCoordinator(temporary, namespace='approval-example')
    seed(coordinator)
    runner = engine(coordinator, Path(temporary) / 'runs.sqlite')
    print(runner.invoke('b.staged_approve', 't.staged_approve', {'id': 'example'},
                        Principal('bob', frozenset({reviewer.id})), run_id='approval-job'))
    print(coordinator.status('approval-job'))
    print(coordinator.read('state:example'))
