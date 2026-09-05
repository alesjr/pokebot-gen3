from __future__ import annotations

import re
import sys
from collections import deque
from threading import Lock


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class WebLogBuffer:
    """Mirror console output while retaining recent complete lines for dashboard."""

    def __init__(self, stream=None, max_lines: int = 1_000):
        self._stream = stream or sys.stdout
        self._lines: deque[dict] = deque(maxlen=max_lines)
        self._partial = ""
        self._sequence = 0
        self._lock = Lock()

    def write(self, value: str) -> int:
        written = self._stream.write(value)
        clean = _ANSI.sub("", value).replace("\r", "")
        with self._lock:
            parts = (self._partial + clean).split("\n")
            self._partial = parts.pop()
            for line in parts:
                if not line:
                    continue
                self._sequence += 1
                lowered = line.lower()
                level = "error" if "error" in lowered or "exception" in lowered else (
                    "warning" if "warning" in lowered or "warn" in lowered else "info"
                )
                category = "capture" if "caught" in lowered or "captur" in lowered else (
                    "encounter" if "encounter" in lowered or "encontro" in lowered else "general"
                )
                self._lines.append(
                    {"sequence": self._sequence, "level": level, "category": category, "text": line}
                )
        return written

    def flush(self) -> None:
        self._stream.flush()

    def isatty(self) -> bool:
        return self._stream.isatty()

    def fileno(self) -> int:
        return self._stream.fileno()

    @property
    def encoding(self) -> str:
        return getattr(self._stream, "encoding", "utf-8")

    def snapshot(self, after: int = 0) -> dict:
        with self._lock:
            return {
                "sequence": self._sequence,
                "lines": [dict(line) for line in self._lines if line["sequence"] > after],
            }


web_log_buffer = WebLogBuffer()
