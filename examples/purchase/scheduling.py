"""Local orchestration; callers supply a clock, while Engine owns business operations."""
from datetime import datetime

from myworkflow.executable import Principal


def aware_time(value):
    result = datetime.fromisoformat(value) if isinstance(value, str) else value
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('Schedule and clock must include a timezone')
    return result


class ScheduledPurchase:
    def __init__(self, engine, clock, due_at):
        self.engine = engine
        self.clock = clock
        self.due_at = aware_time(due_at)
        self.decision = None
        self.sequence = 0
        self.completed = False

    def approve(self, decision, principal):
        # Authorization is checked even for a duplicate event.
        role = self.engine.program.bindings['b.approve']['triggers'][0]['role']
        if role not in principal.roles:
            raise PermissionError('Approval role is required')
        if self.decision is not None:
            return
        self.sequence += 1
        self.engine.invoke('b.approve', 't.approve', {'id': 'purchase-001', 'decision': decision},
                           principal, run_id=f'decision-{self.sequence}')
        self.decision = decision
        self.tick()

    def tick(self):
        if self.completed or self.decision is not True or aware_time(self.clock.now()) < self.due_at:
            return
        system = Principal('scheduler', frozenset({'role.system'}))
        handoff = self.engine.invoke('b.dispatch', 't.timer', {'id': 'purchase-001'}, system, run_id='dispatch')
        target_id = self.engine.program.bindings['b.dispatch']['next_workflow']
        target = next(w for w in self.engine.program.spec['workflows'] if w['id'] == target_id)['bindings'][0]
        self.engine.invoke(target['id'], target['triggers'][0]['id'], {'id': handoff.application_id}, system, run_id='confirm')
        self.completed = True
