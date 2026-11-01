"""Optional bridge: Temporal owns durable orchestration, Engine owns pipelines."""
import asyncio

from temporalio import activity
from temporalio.exceptions import ApplicationError

from myworkflow.runtime import Principal
from myworkflow.contracts.identity import execution_id
from myworkflow.contracts.errors import BusinessError, ContractError, ExecutionFailed, RetryableError
from myworkflow.contracts.results import PipelineResult


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
            result = await asyncio.to_thread(self.engine.invoke_or_raise, request['binding'], request['trigger'], request['payload'], principal, run_id=run_id)
        except Exception as exc:
            cause = exc.cause if isinstance(exc, ExecutionFailed) else exc
            result = PipelineResult.from_exception(exc)
            if isinstance(cause, BusinessError) and not getattr(exc, 'compensation_errors', ()) and not getattr(exc, 'secondary_errors', ()):
                return result.to_dict()
            kind = ('ContractError' if isinstance(cause, ContractError) else 'PermissionDenied' if isinstance(cause, PermissionError)
                    else 'RetryExhausted' if isinstance(cause, RetryableError) else 'BusinessFailure' if isinstance(cause, ValueError)
                    else 'ExecutionFailure')
            details = {'result': result.to_dict(), 'step_id': getattr(exc, 'step_id', None),
                       'compensation_errors': getattr(exc, 'compensation_errors', ()),
                       'secondary_errors': getattr(exc, 'secondary_errors', ())}
            raise ApplicationError(str(exc), details, type=kind, non_retryable=True) from exc
        return result.to_dict()
