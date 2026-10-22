import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest

from PySide6.QtWidgets import QApplication

from camera_monitor.discovery import Device
from support import make_window


class PagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def window_with(self, count, capacity=4):
        window = make_window(self)
        window.wall.change_layout(capacity)
        for index in range(count):
            window.add_device(Device(f'10.0.0.{index + 1}'))
        return window

    def test_a_single_page_hides_the_pager(self):
        window = self.window_with(3, capacity=4)
        self.assertEqual(1, window.page_count())
        self.assertTrue(window.page_prev.isHidden())
        self.assertTrue(window.page_label.isHidden())

    def test_pages_cover_every_device_once(self):
        window = self.window_with(6, capacity=4)
        self.assertEqual(2, window.page_count())
        first = [d.ip for d in window.page_devices()]
        self.assertEqual(4, len(first))
        window.change_page(1)
        second = [d.ip for d in window.page_devices()]
        self.assertEqual(2, len(second))
        self.assertEqual(set(), set(first) & set(second), '同一台设备不能同时出现在两页')
        self.assertEqual(6, len(set(first) | set(second)))

    def test_paging_wraps_around_and_updates_the_label(self):
        window = self.window_with(6, capacity=4)
        self.assertFalse(window.page_label.isHidden())
        window.change_page(-1)
        self.assertEqual(1, window.page)
        self.assertIn('2 / 2', window.page_label.text())
        window.change_page(1)
        self.assertEqual(0, window.page)
        self.assertIn('1 / 2', window.page_label.text())

    def test_the_wall_only_shows_the_current_page(self):
        window = self.window_with(6, capacity=4)
        window.apply_page_to_wall()
        self.app.processEvents()
        self.assertEqual({d.ip for d in window.page_devices()},
                         {tile.player.device.ip for tile in window.wall.tiles})

        window.change_page(1)
        self.app.processEvents()
        self.assertLessEqual(len(window.wall.tiles), 4)
        self.assertEqual({d.ip for d in window.page_devices()},
                         {tile.player.device.ip for tile in window.wall.tiles})


if __name__ == '__main__':
    unittest.main()
