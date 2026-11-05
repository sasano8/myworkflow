"""adapters behavior and invariants."""

import pytest
from myworkflow.adapters.inprocess import (
    InProcessLockProvider,
    LockConflict,
    canonical_key,
)


def test_shared_provider_and_typed_order_independent_keys():
    provider = InProcessLockProvider()
    key = (("second", 2), ("first", "x"))
    assert canonical_key(key) == canonical_key(tuple(reversed(key)))
    assert canonical_key((("a", True),)) != canonical_key((("a", 1),))
    with provider.acquire(key):
        with pytest.raises(LockConflict):
            with provider.acquire(tuple(reversed(key)), timeout=0.001):
                pass
        with provider.acquire(key, namespace="other"):
            pass
    with provider.acquire(key):
        pass
    assert provider._entries == {}
