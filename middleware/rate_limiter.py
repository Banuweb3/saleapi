import time
from threading import Lock

class AuthAttemptLimiter:
    """
    Thread-safe in-memory cache to limit authentication attempts.
    Enforces maximum `max_attempts` per rolling `window_seconds` (default: 4 attempts per hour).
    """
    def __init__(self, max_attempts=4, window_seconds=3600):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = {}  # key -> list of timestamps
        self.lock = Lock()

    def _clean_old_attempts(self, key, now):
        cutoff = now - self.window_seconds
        if key in self.attempts:
            self.attempts[key] = [ts for ts in self.attempts[key] if ts > cutoff]
            if not self.attempts[key]:
                del self.attempts[key]

    def is_rate_limited(self, key: str) -> bool:
        """Returns True if key has reached or exceeded max_attempts in the window."""
        now = time.time()
        with self.lock:
            self._clean_old_attempts(key, now)
            attempts_list = self.attempts.get(key, [])
            return len(attempts_list) >= self.max_attempts

    def record_attempt(self, key: str):
        """Records an authentication attempt for key."""
        now = time.time()
        with self.lock:
            self._clean_old_attempts(key, now)
            if key not in self.attempts:
                self.attempts[key] = []
            self.attempts[key].append(now)

    def get_remaining_attempts(self, key: str) -> int:
        """Returns the number of remaining allowed attempts in the current window."""
        now = time.time()
        with self.lock:
            self._clean_old_attempts(key, now)
            used = len(self.attempts.get(key, []))
            return max(0, self.max_attempts - used)

    def clear(self):
        """Clears all cached attempts (useful for testing)."""
        with self.lock:
            self.attempts.clear()

auth_limiter = AuthAttemptLimiter(max_attempts=4, window_seconds=3600)
