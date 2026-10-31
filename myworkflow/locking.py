"""Named in-process locks. Sharing a provider shares its exclusion domain."""
from contextlib import contextmanager
import json
import math
import threading


class LockConflict(RuntimeError):
    pass


def canonical_key(key, namespace='business'):
    entries = []
    for identity, value in key:
        if type(value) not in (str, int, bool, float) or (type(value) is float and not math.isfinite(value)):
            raise ValueError('Lock keys require finite scalar values')
        if type(value) is float and value == 0:
            value = 0.0
        entries.append((identity, type(value).__name__, value))
    if len({item[0] for item in entries}) != len(entries) or not entries:
        raise ValueError('Lock key references must be nonempty and unique')
    return json.dumps([namespace, sorted(entries)], ensure_ascii=False, separators=(',', ':'))


class InProcessLockProvider:
    """Non-reentrant, bounded waiting, always releases. Not a distributed lock."""
    def __init__(self):
        self._entries = {}
        self._guard = threading.Lock()

    @contextmanager
    def acquire(self, key, *, namespace='business', timeout=0):
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout < 0:
            raise ValueError('Lock timeout must be finite and nonnegative')
        identity = canonical_key(key, namespace)
        with self._guard:
            lock, users = self._entries.get(identity, (threading.Lock(), 0))
            self._entries[identity] = (lock, users + 1)
        acquired = False
        try:
            acquired = lock.acquire(timeout=timeout) if timeout else lock.acquire(blocking=False)
            if not acquired:
                raise LockConflict(f'Lock conflict: {identity}')
            yield
        finally:
            if acquired:
                lock.release()
            with self._guard:
                current, users = self._entries[identity]
                if users == 1:
                    del self._entries[identity]
                else:
                    self._entries[identity] = (current, users - 1)
