"""Reverse compensation with per-registration context snapshots."""
from copy import deepcopy
from dataclasses import replace


class CompensationStack:
    def __init__(self):
        self.entries = []

    def register(self, step_id, handler_id, ctx):
        self.entries.append((step_id, handler_id, deepcopy(dict(ctx.values))))

    def capture(self, ctx):
        step, handler, _ = self.entries[-1]
        self.entries[-1] = (step, handler, deepcopy(dict(ctx.values)))

    def unwind(self, registry, ctx):
        failures = []
        for original, identity, snapshot in reversed(self.entries):
            ctx.events.append((identity, 'compensating'))
            try:
                # Compensation sees the registered inputs, shared services and durable run ID.
                result = registry.handlers[identity](replace(ctx, values=snapshot))
                if result is not None:
                    raise TypeError('Compensation must return None')
                ctx.events.append((identity, 'compensated'))
            except Exception as exc:
                failures.append((identity, str(exc)))
                ctx.events.append((identity, 'compensation-failed'))
        return failures
