"""Stable, bounded IDs; tuple serialization avoids delimiter/normalization collisions."""

import hashlib
import json


def execution_id(*parts):
    return (
        "run-"
        + hashlib.sha256(
            json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
    )


def definition_id(value):
    """Resolve a Python declaration reference at an execution/registration boundary."""
    from myworkflow.contracts.errors import ContractError
    from myworkflow.contracts.annotations import declaration

    value = declaration(value)
    identity = value if isinstance(value, str) else getattr(value, "id", None)
    if not isinstance(identity, str) or not identity:
        raise ContractError("Expected a stable ID or named declaration")
    return identity
