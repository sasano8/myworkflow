from dataclasses import dataclass


@dataclass(frozen=True)
class Definition:
    kind: str
    parser: object
    actor: str
    refs: tuple[str, ...]
    function: object


class Definitions:
    def __init__(self):
        self.items = []

    def step(self, kind, parser, *, actor, refs):
        from myworkflow.acceptance.pytest_bridge import bind_step

        return bind_step(self, kind, parser, actor=actor, refs=refs)

    def resolve(self, kind, text):
        matches = [
            d for d in self.items if d.kind == kind and d.parser.is_matching(text)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one implementation for {kind}: {text}; found {len(matches)}"
            )
        return matches[0]
