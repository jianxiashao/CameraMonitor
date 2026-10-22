import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from camera_monitor.alerts import FreezeWatch
from camera_monitor.bootstrap import watchdog_command
from camera_monitor.recorder import RecorderPool
from support import make_window


def picture(width=64, height=48, color=0x3366cc):
    image = QImage(width, height, QImage.Format.Format_RGB888)
    image.fill(color)
    return image


class FreezeWatchTests(unittest.TestCase):
    def test_reports_only_after_the_picture_stops_changing(self):
        watch = FreezeWatch(seconds=5)
        self.assertIsNone(watch.observe(b'a', 0.0))
        self.assertIsNone(watch.observe(b'b', 1.0), '画面在变就不算卡住')
        self.assertIsNone(watch.observe(b'b', 3.0))
        self.assertIsNone(watch.observe(b'b', 5.9), '还没到 5 秒，不该报')
        self.assertEqual('alert', watch.observe(b'b', 6.0))
        self.assertIsNone(watch.observe(b'b', 7.0), '已经在告警状态，不重复报')
        self.assertEqual('clear', watch.observe(b'c', 8.0), '画面一动就恢复')

    def test_empty_fingerprint_is_ignored(self):
        watch = FreezeWatch(seconds=1)
        self.assertIsNone(watch.observe(b'', 0.0))
        self.assertIsNone(watch.observe(b'', 10.0))


class DiskGuardTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)

    def test_recording_stops_when_the_disk_is_almost_full(self):
        with patch('camera_monitor.recorder.shutil.disk_usage') as usage:
            usage.return_value = SimpleNamespace(total=10 ** 9, used=10 ** 9, free=1024)
            pool = RecorderPool(folder=str(self.base), enabled=True)
            self.addCleanup(pool.close)
            self.assertFalse(pool.add('10.0.0.1', picture()))
            self.assertIn('磁盘剩余不足', pool.stopped_reason)

    def test_a_broken_disk_reading_does_not_stop_recording(self):
        with patch('camera_monitor.recorder.shutil.disk_usage', side_effect=OSError('nope')):
            pool = RecorderPool(folder=str(self.base), enabled=True)
            self.addCleanup(pool.close)
            self.assertTrue(pool.add('10.0.0.2', picture()))


class WatchdogTests(unittest.TestCase):
    def test_watchdog_flag_is_not_forwarded_to_the_child(self):
        with patch('sys.argv', ['CameraMonitor.exe', '--watchdog', '--other']):
            command = watchdog_command()
        self.assertNotIn('--watchdog', command, '转发给子进程会无限套娃')
        self.assertIn('--other', command)

    def test_source_run_uses_the_module_entry_point(self):
        with patch('sys.argv', ['app.py', '--watchdog']):
            command = watchdog_command()
        self.assertEqual(command[1:3], ['-m', 'camera_monitor.app'])


class ScheduledRestartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_restarts_once_per_day_at_the_configured_hour(self):
        window = make_window(self)
        settings = window.device_names.settings
        settings.setValue('monitor/restart_hour', datetime.now().hour)
        settings.sync()

        with patch('camera_monitor.managed_mode.restart_application', return_value=True) as restart:
            window.check_scheduled_restart()
        restart.assert_called_once()

        with patch('camera_monitor.managed_mode.restart_application', return_value=True) as again:
            window.check_scheduled_restart()
        again.assert_not_called()

    def test_disabled_by_default(self):
        window = make_window(self)
        with patch('camera_monitor.managed_mode.restart_application', return_value=True) as restart:
            window.check_scheduled_restart()
        restart.assert_not_called()

    def test_a_different_hour_does_not_trigger(self):
        window = make_window(self)
        settings = window.device_names.settings
        settings.setValue('monitor/restart_hour', (datetime.now().hour + 6) % 24)
        settings.sync()
        with patch('camera_monitor.managed_mode.restart_application', return_value=True) as restart:
            window.check_scheduled_restart()
        restart.assert_not_called()


if __name__ == '__main__':
    unittest.main()
