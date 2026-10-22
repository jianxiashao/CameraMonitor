import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from camera_monitor.alerts import BLACK_FRAMES, BlackScreenWatch, sample_is_black
from camera_monitor.discovery import Device
from support import make_window


def frame(color, width=8, height=8):
    return bytes(color) * (width * height)


class BlackFrameTests(unittest.TestCase):
    def test_all_black_is_reported(self):
        self.assertTrue(sample_is_black(frame((0, 0, 0)), 8, 8, 8 * 3))

    def test_all_white_is_not_reported(self):
        self.assertFalse(sample_is_black(frame((255, 255, 255)), 8, 8, 8 * 3))

    def test_a_bright_spot_breaks_the_verdict(self):
        # 只有角落有一点亮光（夜间画面常见），不算黑屏
        data = bytearray(frame((0, 0, 0)))
        offset = (7 * 8 + 7) * 3
        data[offset] = data[offset + 1] = data[offset + 2] = 200
        self.assertFalse(sample_is_black(bytes(data), 8, 8, 8 * 3))

    def test_empty_or_broken_buffers_do_not_crash(self):
        self.assertFalse(sample_is_black(b'', 8, 8, 24))
        self.assertFalse(sample_is_black(b'\x00' * 4, 8, 8, 24))
        self.assertFalse(sample_is_black(frame((0, 0, 0)), 0, 0, 0))


class BlackScreenWatchTests(unittest.TestCase):
    def test_alerts_only_after_consecutive_dark_frames(self):
        watch = BlackScreenWatch()
        for _ in range(BLACK_FRAMES - 1):
            self.assertIsNone(watch.observe(True))
        self.assertEqual('alert', watch.observe(True))
        # 已经在告警状态，不再重复报
        self.assertIsNone(watch.observe(True))

    def test_a_single_bright_frame_resets_the_counter(self):
        watch = BlackScreenWatch(frames=3)
        watch.observe(True)
        watch.observe(True)
        watch.observe(False)
        self.assertIsNone(watch.observe(True))
        self.assertIsNone(watch.observe(True), '计数被重置，不能连着旧的两帧就报警')
        self.assertEqual('alert', watch.observe(True))

    def test_recovery_is_reported_once(self):
        watch = BlackScreenWatch(frames=1)
        self.assertEqual('alert', watch.observe(True))
        self.assertEqual('clear', watch.observe(False))
        self.assertIsNone(watch.observe(False))


class BlackScreenAlertTests(unittest.TestCase):
    """从解码线程到监控墙格子的完整链路。"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def black_video(self):
        import av
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = os.path.join(folder.name, 'black.mp4')
        with av.open(path, 'w') as container:
            stream = container.add_stream('mpeg4', rate=10)
            stream.width = 64
            stream.height = 48
            stream.pix_fmt = 'yuv420p'
            for _ in range(30):
                picture = av.VideoFrame(64, 48, 'yuv420p')
                # 只把亮度压到 16（黑），色度保持 128（中性），转成 RGB 才真的接近全黑
                picture.planes[0].update(bytes([16]) * picture.planes[0].buffer_size)
                for chroma in picture.planes[1:]:
                    chroma.update(bytes([128]) * chroma.buffer_size)
                for packet in stream.encode(picture):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        return path

    def test_a_black_stream_raises_an_alert(self):
        from camera_monitor.playback import Decoder
        worker = Decoder(self.black_video())
        seen = []
        worker.alert.connect(seen.append, Qt.ConnectionType.DirectConnection)
        worker.start()
        self.assertTrue(worker.wait(8000))
        self.assertTrue(any('全黑' in text for text in seen), f'应当报出黑屏，实际收到 {seen}')

    def test_the_tile_shows_and_clears_the_warning(self):
        window = make_window(self)
        window.wall.add_device(Device('10.0.0.1'))
        tile = window.wall.tiles[0]
        tile.show_alert('画面可能全黑')
        self.assertFalse(tile.alert_badge.isHidden())
        self.assertIn('全黑', tile.alert_badge.text())
        tile.show_alert('')
        self.assertTrue(tile.alert_badge.isHidden())


if __name__ == '__main__':
    unittest.main()
