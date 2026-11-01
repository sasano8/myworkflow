"""Shared message severity contract."""
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
