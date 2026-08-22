import unittest
from queue import Queue

from PIL import Image

from modules.living_dex.video import MjpegFrameStream, offer_latest_frame


class _Emulator:
    def __init__(self):
        self.video_enabled = False
        self.video_changes = []
        self.screen_reads = 0
        self.frame_count = 7

    def get_video_enabled(self):
        return self.video_enabled

    def set_video_enabled(self, enabled):
        self.video_enabled = enabled
        self.video_changes.append(enabled)

    def get_current_screen_image(self):
        self.screen_reads += 1
        return Image.new("RGB", (240, 160), (self.screen_reads, 2, 3))


class TestLivingDexVideo(unittest.TestCase):
    def test_no_subscriber_has_zero_capture_cost(self):
        stream = MjpegFrameStream()
        emulator = _Emulator()
        self.assertFalse(stream.prepare_natural_frame(emulator, now=1.0))
        self.assertEqual(emulator.video_changes, [])
        self.assertEqual(stream.stats().captured_frames, 0)

    def test_capture_uses_existing_natural_frame_and_restores_renderer(self):
        stream = MjpegFrameStream()
        emulator = _Emulator()
        with stream.subscribe():
            self.assertTrue(stream.prepare_natural_frame(emulator, now=1.0))
            self.assertEqual(emulator.frame_count, 7)
            self.assertTrue(stream.finish_natural_frame(emulator))
        self.assertEqual(emulator.frame_count, 7)
        self.assertEqual(emulator.video_changes, [True, False])
        self.assertEqual(emulator.screen_reads, 1)

    def test_all_subscribers_share_same_encoded_jpeg(self):
        stream = MjpegFrameStream()
        emulator = _Emulator()
        with stream.subscribe(), stream.subscribe():
            stream.prepare_natural_frame(emulator, now=1.0)
            stream.finish_natural_frame(emulator)
            sequence, first = stream.wait_for_jpeg(0, timeout=2.0)
            second_sequence, second = stream.wait_for_jpeg(0, timeout=0.0)
        self.assertGreater(sequence, 0)
        self.assertEqual(second_sequence, sequence)
        self.assertIs(first, second)
        self.assertTrue(first.startswith(b"\xff\xd8"))
        self.assertEqual(stream.stats().encoded_frames, 1)

    def test_capture_rate_is_limited(self):
        stream = MjpegFrameStream(fps=2)
        emulator = _Emulator()
        with stream.subscribe():
            self.assertTrue(stream.prepare_natural_frame(emulator, now=1.0))
            stream.finish_natural_frame(emulator)
            self.assertFalse(stream.prepare_natural_frame(emulator, now=1.49))
            self.assertTrue(stream.prepare_natural_frame(emulator, now=1.5))
            stream.cancel_prepared_frame(emulator)

    def test_backpressure_replaces_stale_frame_without_blocking(self):
        frames = Queue(maxsize=1)
        stale = Image.new("RGB", (1, 1), (1, 1, 1))
        latest = Image.new("RGB", (1, 1), (2, 2, 2))
        frames.put_nowait(stale)

        self.assertTrue(offer_latest_frame(frames, latest))
        self.assertIs(frames.get_nowait(), latest)


if __name__ == "__main__":
    unittest.main()
