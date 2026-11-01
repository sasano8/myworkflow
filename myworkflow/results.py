"""Common pipeline completion contract; business artifacts are never return payloads."""
from dataclasses import dataclass
from typing import Literal

MessageLevel = Literal['info', 'warning', 'error', 'critical']


@dataclass(frozen=True)
class Message:
    level: MessageLevel
    text: str

    def __post_init__(self):
        if self.level not in ('info', 'warning', 'error', 'critical') or not isinstance(self.text, str):
            raise ValueError('Message requires a supported level and text')


@dataclass(frozen=True)
class PipelineResult:
    code: int = 0
    messages: tuple[Message, ...] = ()

    def __post_init__(self):
        if type(self.code) is not int or self.code < 0:
            raise ValueError('Result code must be a nonnegative integer')
        if not isinstance(self.messages, tuple) or any(not isinstance(m, Message) for m in self.messages):
            raise ValueError('Result messages must be a tuple of Message')

    @property
    def ok(self) -> bool:
        return self.code == 0

    def to_dict(self) -> dict:
        return {'code': self.code, 'messages': [{'level': m.level, 'text': m.text} for m in self.messages]}

    @classmethod
    def from_exception(cls, error):
        from myworkflow.errors import ExecutionFailed, PipelineError
        cause = error.cause if isinstance(error, ExecutionFailed) else error
        messages = [m for m in getattr(error, 'messages', ()) if isinstance(m, Message)]
        code = cause.code if isinstance(cause, PipelineError) else 255
        messages.append(Message(cause.level if isinstance(cause, PipelineError) else 'error', str(cause)))
        for kind, failures in (('補償', getattr(error, 'compensation_errors', ())),
                               ('後処理', getattr(error, 'secondary_errors', ()))):
            for identity, detail in failures:
                messages.append(Message('critical', f'{kind}失敗：{identity}：{detail}'))
                code = 255
        return cls(code, tuple(messages))
