"""The only adapter depending on pytest-bdd registration and parameter internals."""

from functools import wraps
from myworkflow.acceptance.definitions import Definition


def bind_step(definitions, kind, parser, *, actor, refs):
    from pytest_bdd import given, when, then

    if kind not in ("Context", "Action", "Outcome"):
        raise ValueError(f"Unknown step kind: {kind}")

    def register(fn):
        @wraps(fn)
        def invoke(*args, **kwargs):
            result = fn(*args, **kwargs)
            if kind == "Outcome" and result is not True:
                raise AssertionError(f"{fn.__name__}: expected True, got {result!r}")
            return result

        definitions.items.append(Definition(kind, parser, actor, tuple(refs), fn))
        return {"Context": given, "Action": when, "Outcome": then}[kind](
            parser, stacklevel=2
        )(invoke)

    return register


def case_id(item):
    tags = [m.args[0] for m in item.iter_markers("acceptance_tag")]
    ids = [tag for tag in tags if tag.startswith("scenario.")]
    if not ids:
        return None
    if len(set(ids)) != 1:
        raise ValueError(f"{item.nodeid}: ambiguous scenario IDs")
    example = getattr(item, "callspec", None)
    values = example.params.get("_pytest_bdd_example", {}) if example else {}
    return ids[0] + ("." + values["case"] if "case" in values else "")
