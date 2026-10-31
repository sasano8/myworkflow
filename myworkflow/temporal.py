"""Optional bridge: Temporal owns durable orchestration, Engine owns pipelines."""
from dataclasses import asdict, is_dataclass

from temporalio import activity
from temporalio.exceptions import ApplicationError

from myworkflow.executable import Principal


class PipelineActivity:
    def __init__(self, engine):
        self.engine = engine

    @activity.defn(name='myworkflow.pipeline')
    async def invoke(self, request: dict) -> dict:
        # Principal must come from a trusted ingress adapter, not arbitrary public input.
        principal = Principal(request['actor'], frozenset(request['roles']))
        info = activity.info()
        run_id = f'{info.workflow_id}-{info.workflow_run_id}-{info.activity_id}'.replace('/', '_')
        try:
            result = self.engine.invoke(request['binding'], request['trigger'], request['payload'], principal, run_id=run_id)
        except Exception as exc:
            raise ApplicationError(str(exc), type=type(exc).__name__, non_retryable=True) from exc
        return asdict(result) if is_dataclass(result) else (result or {})
