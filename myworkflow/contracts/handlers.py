"""One ingress/response contract, derived from existing declarations without copying them."""

from dataclasses import dataclass

from myworkflow.contracts.annotations import Extensible, extension_fields
from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.models import Binding, Pipeline, Trigger
from myworkflow.contracts.results import PipelineResult


@dataclass(frozen=True)
class HandlerContract(Extensible):
    binding: Binding
    pipeline: Pipeline
    trigger: Trigger

    def __post_init__(self):
        super().__post_init__()
        if self.binding.pipeline_id != self.pipeline.id or not any(
            self.trigger is t for t in self.binding.triggers
        ):
            raise ContractError(
                "Handler must connect the binding pipeline and one of its declared triggers"
            )

    @property
    def id(self) -> str:
        return f"{self.binding.id}/{self.trigger.id}"

    @property
    def request(self) -> tuple[str, ...]:
        return self.pipeline.inputs

    @property
    def response(self) -> type[PipelineResult] | None:
        return PipelineResult if self.pipeline.reply else None

    def to_dict(self, *, extension_encoder=None):
        return {
            **extension_fields(self, extension_encoder),
            "id": self.id,
            "binding": self.binding.id,
            "pipeline": self.pipeline.id,
            "trigger": self.trigger.id,
            "request": {
                "artifacts": list(self.request),
                "mapping": dict(self.trigger.input_mapping),
                "role": self.trigger.actor_role_id,
            },
            "response": "PipelineResult" if self.response else None,
            "produces": list(self.pipeline.outputs),
        }
