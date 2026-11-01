"""Explicit operator recovery; active runs require a stopped-run confirmation."""
from myworkflow.runtime.ports import RunStatus


class Recovery:
    def __init__(self, journal, objects):
        self.journal, self.objects = journal, objects

    def recover(self, run_id, *, confirmed_stopped=False):
        status, events = self.journal.get(run_id)
        if status not in (RunStatus.MANUAL_RECOVERY, RunStatus.FAILED, RunStatus.COMPENSATED):
            if not (status == RunStatus.RUNNING and confirmed_stopped):
                raise ValueError('Only failed or confirmed-stopped executions can be recovered')
        for slot in ('B', 'A'):
            self.objects.delete(run_id, slot)
        self.journal.record(run_id, events + [('recovery', 'compensated')], RunStatus.COMPENSATED)
