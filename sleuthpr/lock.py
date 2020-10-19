from collections import defaultdict
from contextlib import contextmanager
from threading import Lock
from typing import Dict

_locks: Dict[str, Lock] = {}


# todo: This should be swapped with redlock in prod
@contextmanager
def with_lock(name: str, timeout=1000):
    lock = _locks.get(name)
    if lock is None:
        lock = Lock()
        _locks[name] = lock
    if lock.acquire(timeout=timeout):
        try:
            yield
        finally:
            lock.release()
    else:
        raise TimeoutError()
