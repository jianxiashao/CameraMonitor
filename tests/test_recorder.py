import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import time
import unittest
from pathlib import Path

from PySide6.QtGui import QImage

from camera_monitor.recorder import RecorderPool, RingRecorder, frames_of


def picture(width=64, height=48, color=0x3366cc):
    image = QImage(width, height, QImage.Format.Format_RGB888)
    image.fill(color)
    return image


class RingRecorderTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)

    def test_frames_are_written_and_playable(self):
        recorder = RingRecorder('10.0.0.1', str(self.base))
        self.addCleanup(recorder.close)
        for _ in range(5):
            self.assertTrue(recorder.add(picture()))
        recorder.close()

        segments = recorder.segments()
        self.assertEqual(1, len(segments), '一个分段应当已经落盘')
        self.assertGreater(segments[0][1] and os.path.getsize(segments[0][1]), 0)
        images = list(frames_of(segments))
        self.assertEqual(5, len(images), '写进去几帧就该回放出几帧')

    def test_a_new_segment_starts_after_the_interval(self):
        recorder = RingRecorder('10.0.0.2', str(self.base), segment_seconds=0.01)
        self.addCleanup(recorder.close)
        recorder.add(picture())
        time.sleep(0.02)
        recorder.add(picture())
        recorder.close()
        self.assertEqual(2, len(recorder.segments()))

    def test_expired_segments_are_removed(self):
        recorder = RingRecorder('10.0.0.3', str(self.base), minutes=1)
        self.addCleanup(recorder.close)
        folder = Path(recorder.root)
        folder.mkdir(parents=True, exist_ok=True)
        stale = folder / f'{int(time.time() * 1000) - 3_600_000}.mp4'
        stale.write_bytes(b'old')
        recorder.add(picture())   # 开新段时会顺手清理过期分段
        self.assertFalse(stale.exists(), '超过保留时长的分段要被删掉')

    def test_pool_returns_segments_for_cameras_that_are_not_recording(self):
        pool = RecorderPool(folder=str(self.base))
        self.addCleanup(pool.close)
        self.assertTrue(pool.add('10.0.0.9', picture()))
        self.assertEqual(1, len(pool.segments('10.0.0.9')))
        self.assertEqual([], pool.segments('10.0.0.10'))

    def test_disabled_pool_does_not_write(self):
        pool = RecorderPool(folder=str(self.base), enabled=False)
        self.addCleanup(pool.close)
        self.assertFalse(pool.add('10.0.0.11', picture()))
        self.assertEqual([], pool.segments('10.0.0.11'))


if __name__ == '__main__':
    unittest.main()
