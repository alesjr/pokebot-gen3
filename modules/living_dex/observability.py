from __future__ import annotations

from collections import deque
from datetime import datetime
from threading import Lock


_started_at = datetime.now().astimezone()
_events: deque[dict] = deque(maxlen=100)
_lock = Lock()
_reset_count = 0
_encounter_count = 0


def record_event(kind: str, message: str, **details) -> None:
    global _reset_count, _encounter_count
    with _lock:
        if kind == "reset":
            _reset_count += 1
        elif kind == "encounter":
            _encounter_count += 1
        _events.appendleft(
            {
                "time": datetime.now().astimezone().isoformat(timespec="seconds"),
                "kind": kind,
                "message": message,
                "details": details,
            }
        )


def runtime_events() -> dict:
    with _lock:
        return {
            "started_at": _started_at.isoformat(timespec="seconds"),
            "reset_count": _reset_count,
            "encounter_count": _encounter_count,
            "events": list(_events),
        }
