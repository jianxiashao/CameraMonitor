import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PySide6.QtCore import QSettings

from camera_monitor.diagnostics import collect, is_sensitive, redacted_settings


class FakePlayer:
    class _Box:
        def __init__(self, text):
            self._text = text

        def toPlainText(self):
            return self._text

    class _Device:
        ip = '10.0.0.9'

    device = _Device()

    def __init__(self, detail=''):
        self.connection_diagnostics = self._Box(detail)


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)

    def test_sensitive_keys_never_reach_the_archive(self):
        self.assertTrue(is_sensitive('camera/password'))
        self.assertTrue(is_sensitive('cloud/token'))
        self.assertFalse(is_sensitive('monitor/layout'))

        settings = QSettings(str(self.base / 'settings.ini'), QSettings.Format.IniFormat)
        settings.setValue('camera/password', 'top-secret')
        settings.setValue('cloud/token', 'cm1.abc')
        settings.setValue('monitor/layout', '9')
        settings.sync()

        exported = redacted_settings(settings)
        self.assertEqual('9', exported['monitor/layout'])
        self.assertNotIn('camera/password', exported)
        self.assertNotIn('cloud/token', exported)

    def test_archive_contains_system_settings_logs_and_player_diagnostics(self):
        settings = QSettings(str(self.base / 'settings.ini'), QSettings.Format.IniFormat)
        settings.setValue('monitor/layout', '9')
        settings.sync()
        logs = self.base / 'logs'
        logs.mkdir()
        (logs / 'camera_monitor.log').write_text('2026-01-01 启动\n', encoding='utf-8')

        target = self.base / 'bundle'
        saved = collect(target, log_dir=str(logs), settings=settings,
                        players=[FakePlayer('TCP · 建立连接 · 超时')])

        self.assertEqual(str(target) + '.zip', saved)
        with zipfile.ZipFile(saved) as archive:
            names = set(archive.namelist())
            self.assertIn('system.txt', names)
            self.assertIn('settings.json', names)
            self.assertIn('players.txt', names)
            self.assertIn('logs/camera_monitor.log', names)
            self.assertIn('Camera Monitor', archive.read('system.txt').decode('utf-8'))
            self.assertIn('超时', archive.read('players.txt').decode('utf-8'))
            data = json.loads(archive.read('settings.json').decode('utf-8'))
            self.assertEqual('9', data['monitor/layout'])

    def test_missing_log_folder_is_not_fatal(self):
        saved = collect(self.base / 'bundle2', log_dir=str(self.base / 'nope'))
        with zipfile.ZipFile(saved) as archive:
            self.assertIn('system.txt', archive.namelist())


if __name__ == '__main__':
    unittest.main()
