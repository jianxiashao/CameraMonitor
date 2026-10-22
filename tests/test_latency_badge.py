import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest

from PySide6.QtWidgets import QApplication

from camera_monitor.discovery import Device
from support import make_window


class LatencyBadgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tile(self):
        window = make_window(self)
        window.wall.add_device(Device('10.0.0.1'))
        return window.wall.tiles[0]

    def test_badge_wording_follows_the_delay(self):
        tile = self.tile()
        for behind, expected in ((0.2, '实时'), (1.2, '延迟'), (5.0, '追赶')):
            tile.show_latency(behind)
            self.assertIn(expected, tile.latency_badge.text())
            self.assertFalse(tile.latency_badge.isHidden(), '收到延迟数据后指示灯要显示出来')

    def test_badge_sits_inside_the_tile(self):
        tile = self.tile()
        tile.resize(400, 240)
        tile.player.surface.resize(400, 240)
        tile.show_latency(0.3)
        badge = tile.latency_badge
        self.assertGreaterEqual(badge.x(), 0)
        self.assertGreaterEqual(badge.y(), 0)
        self.assertLessEqual(badge.x() + badge.width(), tile.player.surface.width())

    def test_a_new_decoder_reports_latency_to_the_tile(self):
        # 播放器把解码线程的延迟信号转发给格子，不需要界面自己算
        tile = self.tile()
        forwarded = []
        tile.player.latency_changed.connect(forwarded.append)
        tile.player.latency_changed.emit(1.5)
        self.assertEqual([1.5], forwarded)


if __name__ == '__main__':
    unittest.main()
