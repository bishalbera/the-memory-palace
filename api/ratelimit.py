"""In-memory rate limiting to protect LLM credits on a public demo.

Single-instance only (which this app already is — Kuzu takes a process lock),
so plain in-memory counters are enough; no Redis required. All limits are
tunable via environment variables.
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

MAX_TURNS_PER_SESSION = int(os.environ.get("MAX_TURNS_PER_SESSION", "30"))

IP_ACTIONS_PER_MIN = int(os.environ.get("IP_ACTIONS_PER_MIN", "12"))
IP_SESSIONS_PER_HOUR = int(os.environ.get("IP_SESSIONS_PER_HOUR", "6"))

GLOBAL_ACTIONS_PER_DAY = int(os.environ.get("GLOBAL_ACTIONS_PER_DAY", "200"))

_GLOBAL_MSG = "The manor is resting — today's demo budget has been spent. Please return tomorrow."

_lock = threading.Lock()
_ip_actions: dict[str, deque] = defaultdict(deque)   # ip -> action timestamps (last minute)
_ip_sessions: dict[str, deque] = defaultdict(deque)  # ip -> session-start timestamps (last hour)
_global_day: deque = deque()                          # all paid ops (last 24h)


def _prune(dq: deque, window: float, now: float) -> None:
    while dq and now - dq[0] > window:
        dq.popleft()


def allow_session(ip: str) -> tuple[bool, str]:
    """Gate a new game. Returns (allowed, reason_if_blocked)."""
    now = time.time()
    with _lock:
        _prune(_global_day, 86400, now)
        if len(_global_day) >= GLOBAL_ACTIONS_PER_DAY:
            return False, _GLOBAL_MSG
        dq = _ip_sessions[ip]
        _prune(dq, 3600, now)
        if len(dq) >= IP_SESSIONS_PER_HOUR:
            return False, "Too many games started from your connection. Please try again later."
        dq.append(now)
        _global_day.append(now)
        return True, ""


def allow_action(ip: str) -> tuple[bool, str]:
    """Gate a single turn. Returns (allowed, reason_if_blocked)."""
    now = time.time()
    with _lock:
        _prune(_global_day, 86400, now)
        if len(_global_day) >= GLOBAL_ACTIONS_PER_DAY:
            return False, _GLOBAL_MSG
        dq = _ip_actions[ip]
        _prune(dq, 60, now)
        if len(dq) >= IP_ACTIONS_PER_MIN:
            return False, "You're moving quickly, Detective — take a breath and try again in a moment."
        dq.append(now)
        _global_day.append(now)
        return True, ""


def client_ip(conn) -> str:
    """Best-effort client IP for a Request or WebSocket (honours the proxy header)."""
    xff = conn.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return conn.client.host if conn.client else "unknown"
