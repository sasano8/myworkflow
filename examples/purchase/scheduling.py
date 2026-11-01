"""Local orchestration; callers supply a clock, while Engine owns business operations."""
from datetime import datetime

from myworkflow.executable import Principal
from myworkflow.identity import execution_id


def aware_time(value):
    result = datetime.fromisoformat(value) if isinstance(value, str) else value
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('Schedule and clock must include a timezone')
    return result


class ScheduledPurchase:
    def __init__(self, engine, clock, due_at, *, application_id, run_id):
        self.engine = engine
        self.application_id = application_id
        self.run_id = run_id
        self.clock = clock
        self.due_at = aware_time(due_at)
        self.decision = None
        self.sequence = 0
        self.completed = False

    def approve(self, decision, principal):
        # Authorization is checked even for a duplicate event.
        role = self.engine.program.trigger('b.approve', 't.approve').actor_role_id
        if role not in principal.roles:
            raise PermissionError('Approval role is required')
        if self.decision is not None:
            return
        self.sequence += 1
        self.engine.invoke_or_raise('b.approve', 't.approve', self.engine.program.payload('b.approve', 't.approve', {'application_id': self.application_id, 'decision': decision}),
                           principal, run_id=execution_id(self.run_id, 'decision', self.sequence))
        self.decision = decision
        self.tick()

    def tick(self):
        if self.completed or self.decision is not True or aware_time(self.clock.now()) < self.due_at:
            return
        system = Principal('scheduler', frozenset({'role.system'}))
        self.engine.invoke_or_raise('b.dispatch', 't.timer', self.engine.program.payload('b.dispatch', 't.timer', {'application_id': self.application_id}), system, run_id=execution_id(self.run_id, 'dispatch'))
        target = self.engine.program.next_binding('b.dispatch', 'b.confirm')
        payload = self.engine.program.payload(target.id, 't.confirm', {'application_id': self.application_id})
        self.engine.invoke_or_raise(target.id, 't.confirm', payload, system, run_id=execution_id(self.run_id, 'confirm'))
        self.completed = True
