from __future__ import annotations

import io
import queue
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from PIL import Image


def offer_latest_frame(target: queue.Queue[Image.Image], frame: Image.Image) -> bool:
    """Offer frame without blocking; replace queued stale frame when full."""
    dropped = False
    try:
        target.put_nowait(frame)
    except queue.Full:
        try:
            target.get_nowait()
            target.task_done()
            dropped = True
        except queue.Empty:
            pass
        target.put_nowait(frame)
    return dropped


@dataclass(frozen=True)
class VideoStreamStats:
    subscribers: int
    captured_frames: int
    encoded_frames: int
    dropped_frames: int


class MjpegFrameStream:
    """Capture natural emulator frames and publish one shared JPEG stream."""

    def __init__(self, *, fps: int = 15, jpeg_quality: int = 75):
        if fps <= 0:
            raise ValueError("fps must be positive")
        if not 1 <= jpeg_quality <= 95:
            raise ValueError("jpeg_quality must be between 1 and 95")

        self._capture_interval = 1 / fps
        self._jpeg_quality = jpeg_quality
        self._raw_frames: queue.Queue[Image.Image] = queue.Queue(maxsize=1)
        self._condition = threading.Condition()
        self._subscribers = 0
        self._capture_prepared = False
        self._restore_video_enabled = False
        self._next_capture_at = 0.0
        self._latest_jpeg: bytes | None = None
        self._sequence = 0
        self._captured_frames = 0
        self._encoded_frames = 0
        self._dropped_frames = 0
        threading.Thread(target=self._encode_frames, name="living-dex-jpeg", daemon=True).start()

    @contextmanager
    def subscribe(self) -> Iterator[None]:
        with self._condition:
            self._subscribers += 1
            self._next_capture_at = 0.0
        try:
            yield
        finally:
            with self._condition:
                self._subscribers -= 1

    def prepare_natural_frame(self, emulator, *, now: float | None = None) -> bool:
        """Enable rendering when next regular emulation frame should be captured."""
        timestamp = time.monotonic() if now is None else now
        with self._condition:
            if self._capture_prepared or self._subscribers == 0 or timestamp < self._next_capture_at:
                return False
            self._capture_prepared = True
            self._next_capture_at = timestamp + self._capture_interval

        self._restore_video_enabled = emulator.get_video_enabled()
        if not self._restore_video_enabled:
            emulator.set_video_enabled(True)
        return True

    def finish_natural_frame(self, emulator) -> bool:
        """Copy rendered framebuffer after regular frame; never advances emulation."""
        with self._condition:
            if not self._capture_prepared:
                return False
            self._capture_prepared = False

        try:
            frame = emulator.get_current_screen_image().convert("RGB").copy()
            self._captured_frames += 1
            self._offer_latest(frame)
        finally:
            if not self._restore_video_enabled:
                emulator.set_video_enabled(False)
        return True

    def cancel_prepared_frame(self, emulator) -> None:
        """Restore renderer if regular frame execution failed."""
        with self._condition:
            if not self._capture_prepared:
                return
            self._capture_prepared = False
        if not self._restore_video_enabled:
            emulator.set_video_enabled(False)

    def wait_for_jpeg(self, sequence: int, timeout: float = 2.0) -> tuple[int, bytes | None]:
        with self._condition:
            self._condition.wait_for(lambda: self._sequence > sequence, timeout=timeout)
            return self._sequence, self._latest_jpeg

    def stats(self) -> VideoStreamStats:
        with self._condition:
            return VideoStreamStats(
                subscribers=self._subscribers,
                captured_frames=self._captured_frames,
                encoded_frames=self._encoded_frames,
                dropped_frames=self._dropped_frames,
            )

    def _offer_latest(self, frame: Image.Image) -> None:
        if offer_latest_frame(self._raw_frames, frame):
            with self._condition:
                self._dropped_frames += 1

    def _encode_frames(self) -> None:
        while True:
            frame = self._raw_frames.get()
            try:
                output = io.BytesIO()
                frame.save(output, format="JPEG", quality=self._jpeg_quality, optimize=False)
                jpeg = output.getvalue()
                with self._condition:
                    self._latest_jpeg = jpeg
                    self._sequence += 1
                    self._encoded_frames += 1
                    self._condition.notify_all()
            finally:
                self._raw_frames.task_done()
