from collections.abc import MutableMapping
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from typing import get_type_hints
from myworkflow.contracts.errors import ContractError, RetryableError, ExecutionFailed
from myworkflow.runtime.context import Context
from myworkflow.runtime.transitions import TransitionRuntime
from myworkflow.contracts.names import class_name
from myworkflow.runtime.compensation import CompensationStack
from myworkflow.contracts.results import PipelineResult
from myworkflow.contracts.identity import definition_id
from myworkflow.runtime.ports import ExecutionStore, LockProvider, RunStatus

from myworkflow.contracts.value_objects import PRIMITIVES as TYPES

@dataclass(frozen=True)
class Principal:
    id: str
    roles: frozenset[str]


class Engine:
    def __init__(self, program, registry, services, interfaces=None, *, locks: LockProvider | None = None, store: ExecutionStore | None = None, transitions: TransitionRuntime | None = None):
        program.check(registry)
        self.program, self.registry, self.services = program, registry, services
        self.interfaces = interfaces
        self.transitions = transitions
        if transitions is not None and transitions.catalog is not program.model:
            raise ContractError('Transition runtime must use the Engine catalog')
        self.locks = locks or getattr(services, 'lock_provider', None)
        self.store = store or getattr(services, 'execution_store', None)
        if self.store is None or (any((s.kind == 'lock' for s in program.steps.values())) and self.locks is None):
            raise ContractError('Engine requires an ExecutionStore and a LockProvider for locking steps')
        if interfaces:
            for p in program.plans.values():
                name = class_name(p.id)
                request = getattr(interfaces, name + 'Request', None)
                expected = {program.artifacts[i].key: (program.artifacts[i].value_object.model if program.artifacts[i].value_object else TYPES[program.artifacts[i].type]) for i in p.inputs}
                if request is None or not is_dataclass(request) or get_type_hints(request) != expected:
                    raise ContractError(f'{p.id}: stale or invalid Request interface')
                if getattr(interfaces, name + 'Response', None) is not PipelineResult:
                    raise ContractError(f'{p.id}: stale or invalid Response interface')

    def invoke(self, binding_id, trigger_id, payload, principal, *, run_id) -> PipelineResult:
        try:
            return self.invoke_or_raise(binding_id, trigger_id, payload, principal, run_id=run_id)
        except Exception as exc:
            return PipelineResult.from_exception(exc)

    def invoke_or_raise(self, binding_id, trigger_id, payload, principal, *, run_id) -> PipelineResult:
        b = self.program.binding(binding_id)
        t = self.program.trigger(b.id, trigger_id)
        if t.actor_role_id not in principal.roles:
            raise PermissionError(f'{t.id}: {principal.id} lacks {t.actor_role_id}')
        if set(payload) != {source for _, source in t.input_mapping}:
            raise ContractError(f"{t.id}: payload fields do not match mapping")
        values = {self.program.artifacts[a].key: payload[source] for a, source in t.input_mapping}
        return self._run_or_raise(b.pipeline_id, values, actor=principal.id, run_id=run_id, binding_id=b.id, trigger_id=t.id)

    def run(self, pipeline_id, request, *, actor, run_id) -> PipelineResult:
        try:
            return self.run_or_raise(pipeline_id, request, actor=actor, run_id=run_id)
        except Exception as exc:
            return PipelineResult.from_exception(exc)

    def run_or_raise(self, pipeline_id, request, *, actor, run_id) -> PipelineResult:
        pipeline_id = definition_id(pipeline_id)
        if self.transitions is not None and self.transitions.governs_pipeline(pipeline_id):
            raise ContractError('Transition-controlled pipelines must use invoke with an authorized trigger')
        return self._run_or_raise(pipeline_id, request, actor=actor, run_id=run_id)

    def _run_or_raise(self, pipeline_id, request, *, actor, run_id, binding_id=None, trigger_id=None):
        p = self.program.plans[pipeline_id]
        values = asdict(request) if is_dataclass(request) else dict(request)
        values = self.program.values(p.inputs, values, pipeline_id)
        ctx = Context(values, self.services, run_id, actor, [])
        self.store.begin(run_id)
        compensations = CompensationStack()
        failure_id = pipeline_id
        secondary = []
        stack = ExitStack()
        session = None
        try:
            try:
                if self.transitions is not None and binding_id is not None:
                    session = self.transitions.begin(ctx, binding_id, trigger_id)
                for s in p.steps:
                    failure_id = s.id
                    if s.kind == "lock":
                        keys = tuple((a, values[self.program.artifacts[a].key]) for a in s.reads)
                        stack.enter_context(self.locks.acquire(keys, namespace=s.namespace, timeout=s.timeout))
                        ctx.events.append((s.id, 'locked'))
                        continue
                    condition = s.when
                    if condition and values[self.program.artifacts[condition[0]].key] != condition[1]:
                        ctx.events.append((s.id, 'skipped'))
                        continue
                    if s.compensate:
                        # Register before executing: remote success with a lost response is ambiguous.
                        compensations.register(s.id, s.compensate, ctx)
                    for attempt in range(s.attempts):
                        try:
                            self._call(s.id, ctx, s.reads, s.writes)
                            ctx.events.append((s.id, 'completed'))
                            break
                        except RetryableError:
                            if attempt + 1 == s.attempts:
                                raise
                            ctx.events.append((s.id, 'retry'))
                        finally:
                            if s.compensate:
                                compensations.capture(ctx)
                failure_id = pipeline_id + "/response"
                produced = {self.program.artifacts[a].key: values[self.program.artifacts[a].key] for a in p.outputs}
                values.update(self.program.values(p.outputs, produced, pipeline_id))
                if session is not None:
                    failure_id = pipeline_id + "/transition"
                    session.finish(ctx)
                response = PipelineResult(messages=tuple(ctx.messages))
                failure_id = pipeline_id + "/unlock"
                stack.close()
                failure_id = pipeline_id + "/journal"
                self.store.record(run_id, ctx.events, RunStatus.COMPLETED)
                return response
            except Exception as exc:
                ctx.events.append((failure_id, 'failed'))
                if session is not None and session.prepare_attempted:
                    # Do not undo side effects after a potentially successful durable commit.
                    errors = []
                    secondary.append(('transition-recovery',
                                      f'Inspect coordinator job {run_id}; automatic compensation was withheld'))
                else:
                    errors = compensations.unwind(self.registry, ctx)
                try:
                    stack.close()
                except Exception as cleanup_error:
                    secondary.append(('lock-release', str(cleanup_error)))
                status = RunStatus.MANUAL_RECOVERY if errors or secondary else RunStatus.FAILED
                try:
                    self.store.record(run_id, ctx.events, status)
                except Exception as journal_error:
                    secondary.append(('journal', str(journal_error)))
                failure = ExecutionFailed(failure_id, exc, errors)
                failure.secondary_errors = tuple(secondary)
                failure.messages = tuple(ctx.messages)
                raise failure from exc
        finally:
            if session is not None:
                session.close()
            # close() is idempotent; original failures are preserved above.
            stack.close()

    def run_internal(self, pipeline_id, request, *, actor, run_id):
        """Trusted internal entry; public inputs must use invoke for authorization."""
        return self.run(pipeline_id, request, actor=actor, run_id=run_id)

    def _call(self, identity, ctx, reads, writes):
        keys = {self.program.artifacts[a].key for a in reads}
        selected = {k: ctx.values[k] for k in keys if k in ctx.values}
        ctx.values.update(self.program.values(reads, selected, identity))
        before = deepcopy(ctx.values)
        allowed = {self.program.artifacts[a].key for a in writes}
        raw = ctx.values
        ctx.values = StepValues(raw, keys, allowed, identity)
        try:
            if self.registry.handlers[identity](ctx) is not None:
                raise ContractError(f"{identity}: handler must return None")
        finally:
            ctx.values = raw
        changed = {k for k in before.keys() | ctx.values.keys() if k not in before or k not in ctx.values or before[k] != ctx.values[k]}
        if changed - allowed:
            raise ContractError(f"{identity}: undeclared context writes {sorted(changed - allowed)}")
        ctx.values.update(self.program.values(writes, {k: ctx.values[k] for k in allowed if k in ctx.values}, identity))


class StepValues(MutableMapping):
    def __init__(self, values, reads, writes, identity):
        self.values, self.reads, self.writes, self.identity = values, reads, writes, identity

    def __getitem__(self, key):
        if key not in self.reads and key not in self.writes:
            raise ContractError(f"{self.identity}: undeclared context read {key}")
        return self.values[key]

    def __setitem__(self, key, value):
        if key not in self.writes:
            raise ContractError(f"{self.identity}: undeclared context write {key}")
        self.values[key] = value

    def __delitem__(self, key):
        raise ContractError(f"{self.identity}: context deletion is not supported")

    def __iter__(self):
        return iter(k for k in self.values if k in self.reads or k in self.writes)

    def __len__(self):
        return sum(1 for _ in self)
