"""Common pipeline completion contract; business artifacts are never return payloads."""
from dataclasses import dataclass

DEFAULT_ERROR_CODE = 1

from myworkflow.contracts.messages import Message, MessageLevel


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
        from myworkflow.contracts.errors import ExecutionFailed, PipelineError
        cause = error.cause if isinstance(error, ExecutionFailed) else error
        messages = [m for m in getattr(error, 'messages', ()) if isinstance(m, Message)]
        code = cause.code if isinstance(cause, PipelineError) else DEFAULT_ERROR_CODE
        messages.append(Message(cause.level if isinstance(cause, PipelineError) else 'error', str(cause)))
        for kind, failures in (('補償', getattr(error, 'compensation_errors', ())),
                               ('後処理', getattr(error, 'secondary_errors', ()))):
            for identity, detail in failures:
                messages.append(Message('critical', f'{kind}失敗：{identity}：{detail}'))
                code = DEFAULT_ERROR_CODE
        return cls(code, tuple(messages))
