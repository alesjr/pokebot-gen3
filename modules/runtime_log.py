"""Bounded, thread-safe copy of Rich console output for authenticated UI clients."""

from __future__ import annotations

import re
import sys
from collections import deque
from threading import Lock
from typing import TextIO

ANSI_ESCAPE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class RuntimeLog:
    def __init__(self, output: TextIO | None = None, max_lines: int = 500) -> None:
        self.output = output or sys.stdout
        self.lines: deque[tuple[int, str]] = deque(maxlen=max_lines)
        self.pending = ""
        self.sequence = 0
        self.lock = Lock()

    def write(self, value: str) -> int:
        written = self.output.write(value)
        clean = ANSI_ESCAPE.sub("", value).replace("\r", "")
        with self.lock:
            parts = (self.pending + clean).split("\n")
            self.pending = parts.pop()
            for line in parts:
                self.sequence += 1
                self.lines.append((self.sequence, line))
        return written

    def flush(self) -> None:
        self.output.flush()

    def isatty(self) -> bool:
        return self.output.isatty()

    @property
    def encoding(self) -> str:
        return self.output.encoding or "utf-8"

    def snapshot(self, after: int = 0) -> dict:
        with self.lock:
            lines = [{"sequence": sequence, "text": line} for sequence, line in self.lines if sequence > after]
            return {"sequence": self.sequence, "lines": lines}


runtime_log = RuntimeLog()
