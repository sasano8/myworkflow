"""Explicit fault/observation wrappers for the sample's development adapters."""
from examples.apps.purchase.repository import PurchaseRepository
from myworkflow.errors import RetryableError


class Faults:
    def __init__(self):
        self.rules = {}
        self.calls = []

    def inject(self, operation, point):
        queue = self.rules.get(operation, [])
        if queue and queue[0] == point:
            queue.pop(0)
            raise RetryableError(f'Injected {operation}:{point}')


class ObservedRepository(PurchaseRepository):
    def __init__(self, database, faults):
        super().__init__(database)
        self.faults = faults

    def after_order_insert(self):
        self.faults.inject('confirm', 'after-insert')


class ObservedObjectStore:
    def __init__(self, inner, faults):
        self.inner, self.faults = inner, faults

    def put(self, run_id, slot, body):
        self.faults.calls.append(f'put-{slot}')
        self.inner.prepare(run_id, slot)
        self.faults.inject(f'put-{slot}', 'before')
        result = self.inner.put(run_id, slot, body)
        self.faults.inject(f'put-{slot}', 'after')
        return result

    def delete(self, run_id, slot):
        self.faults.calls.append(f'delete-{slot}')
        self.faults.inject(f'delete-{slot}', 'before')
        return self.inner.delete(run_id, slot)
