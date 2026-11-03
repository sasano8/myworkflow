"""Ingress authorization/mapping and response adaptation, composed around a pipeline runner."""
from collections.abc import Callable
from dataclasses import dataclass

from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.handlers import HandlerContract
from myworkflow.contracts.results import PipelineResult


@dataclass(frozen=True)
class Principal:
    id: str
    roles: frozenset[str]


class Handler:
    def __init__(self, program, contract: HandlerContract, run: Callable[..., PipelineResult]):
        if program.binding(contract.binding.id) is not contract.binding or program.plans.get(contract.pipeline.id) is not contract.pipeline:
            raise ContractError('Handler contract must belong to its program')
        self.program, self.contract, self.run = program, contract, run

    def invoke_or_raise(self, payload, principal: Principal, *, run_id) -> PipelineResult:
        contract = self.contract
        trigger = contract.trigger
        if trigger.actor_role_id not in principal.roles:
            raise PermissionError(f'{trigger.id}: {principal.id} lacks {trigger.actor_role_id}')
        if set(payload) != {source for _, source in trigger.input_mapping}:
            raise ContractError(f'{trigger.id}: payload fields do not match mapping')
        values = {self.program.artifacts[a].key: payload[source] for a, source in trigger.input_mapping}
        return self.run(contract.pipeline.id, values, actor=principal.id, run_id=run_id,
                        binding_id=contract.binding.id, trigger_id=trigger.id)

    def invoke(self, payload, principal: Principal, *, run_id) -> PipelineResult:
        try:
            return self.invoke_or_raise(payload, principal, run_id=run_id)
        except Exception as exc:
            return PipelineResult.from_exception(exc)

    def handle(self, payload, principal: Principal, *, run_id, respond=PipelineResult.to_dict):
        result = self.invoke(payload, principal, run_id=run_id)
        return respond(result) if self.contract.response is not None else None
