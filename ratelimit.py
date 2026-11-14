"""Login throttling. In-memory sliding window: fine for ONE server process.
When you run several servers on AWS, swap this for Flask-Limiter backed by Redis."""
import time
from collections import deque


class LoginLimiter:
    def __init__(self, max_attempts=5, window_seconds=600, clock=time.monotonic):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self.clock = clock
        self._fails = {}

    def _count(self, key):
        q = self._fails.get(key)
        if not q:
            return 0
        cutoff = self.clock() - self.window
        while q and q[0] <= cutoff:
            q.popleft()
        if not q:
            del self._fails[key]
            return 0
        return len(q)

    def is_blocked(self, ip, email):
        """Blocked after N failures for one account from one IP, or 4N failures from one IP overall."""
        return (self._count(f"acct:{ip}|{email}") >= self.max_attempts
                or self._count(f"ip:{ip}") >= self.max_attempts * 4)

    def record_failure(self, ip, email):
        now = self.clock()
        for key in (f"acct:{ip}|{email}", f"ip:{ip}"):
            self._fails.setdefault(key, deque()).append(now)

    def reset(self, ip, email):
        self._fails.pop(f"acct:{ip}|{email}", None)
