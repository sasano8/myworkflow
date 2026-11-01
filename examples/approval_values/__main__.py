"""Run the example catalog."""
from pathlib import Path
from tempfile import TemporaryDirectory
from myworkflow.adapters.local_artifacts import TemporaryArtifactCoordinator
from myworkflow.executable import Principal
from examples.approval_values.application import engine, reviewer, seed, Approval


with TemporaryDirectory() as temporary:
    coordinator = TemporaryArtifactCoordinator(temporary, namespace='guarded-approval')
    seed(coordinator)
    runner = engine(coordinator, Path(temporary) / 'runs.sqlite')
    print(runner.invoke(Approval.execute, Approval.requested, {'id': 'example'},
                        Principal('bob', frozenset({reviewer.id})), run_id='approval-job'))
    print(coordinator.read('application:example'))
