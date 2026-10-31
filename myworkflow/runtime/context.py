from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionMetadata:
    run_id: str
    actor: str


@dataclass
class Context:
    values: dict
    services: object
    run_id: str
    actor: str
    events: list

    @property
    def execution(self):
        return ExecutionMetadata(self.run_id, self.actor)
