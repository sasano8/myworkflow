from dataclasses import dataclass

@dataclass(frozen=True)
class Case:
    id: str
    scenario_id: str
    name: str
    requirements: tuple[str, ...]
    steps: tuple[dict, ...]
    tags: tuple[str, ...]
    uri: str
    line: int
    source_hash: str
