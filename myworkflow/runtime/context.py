from dataclasses import dataclass, field
from myworkflow.results import Message, MessageLevel


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

    messages: list[Message] = field(default_factory=list)

    def add_message(self, text: str, *, level: MessageLevel = 'info') -> None:
        self.messages.append(Message(level, text))

    @property
    def execution(self):
        return ExecutionMetadata(self.run_id, self.actor)
