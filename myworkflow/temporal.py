"""Optional bridge: Temporal owns durable orchestration, Engine owns pipelines."""
import asyncio
from dataclasses import asdict, is_dataclass

from temporalio import activity
from temporalio.exceptions import ApplicationError

from myworkflow.executable import Principal
from myworkflow.identity import execution_id
from myworkflow.errors import ContractError, ExecutionFailed, RetryableError


class PipelineActivity:
    def __init__(self, engine):
        self.engine = engine

    @activity.defn(name='myworkflow.pipeline')
    async def invoke(self, request: dict) -> dict:
        # Principal must come from a trusted ingress adapter, not arbitrary public input.
        principal = Principal(request['actor'], frozenset(request['roles']))
        info = activity.info()
        run_id = execution_id(info.workflow_id, info.workflow_run_id, info.activity_id)
        try:
            result = await asyncio.to_thread(self.engine.invoke, request['binding'], request['trigger'], request['payload'], principal, run_id=run_id)
        except Exception as exc:
            cause = exc.cause if isinstance(exc, ExecutionFailed) else exc
            kind = ('ContractError' if isinstance(cause, ContractError) else 'PermissionDenied' if isinstance(cause, PermissionError)
                    else 'RetryExhausted' if isinstance(cause, RetryableError) else 'BusinessFailure' if isinstance(cause, ValueError)
                    else 'ExecutionFailure')
            details = {'step_id': getattr(exc, 'step_id', None),
                       'compensation_errors': getattr(exc, 'compensation_errors', ()),
                       'secondary_errors': getattr(exc, 'secondary_errors', ())}
            raise ApplicationError(str(exc), details, type=kind, non_retryable=True) from exc
        return asdict(result) if is_dataclass(result) else (result or {})
