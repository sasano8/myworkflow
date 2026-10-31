"""Stable, bounded IDs; tuple serialization avoids delimiter/normalization collisions."""
import hashlib
import json


def execution_id(*parts):
    return 'run-' + hashlib.sha256(json.dumps(parts, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
