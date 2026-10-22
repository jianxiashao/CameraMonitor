import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest

from PySide6.QtCore import QSettings

from camera_monitor import theme


class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.settings = QSettings(os.path.join(self.folder.name, 'ui.ini'), QSettings.Format.IniFormat)

    def test_default_is_light(self):
        self.assertEqual(theme.LIGHT, theme.current(self.settings))

    def test_toggle_switches_and_remembers(self):
        self.assertEqual(theme.DARK, theme.toggle(self.settings))
        self.assertEqual(theme.DARK, theme.current(self.settings))
        self.assertEqual(theme.LIGHT, theme.toggle(self.settings))
        self.assertEqual(theme.LIGHT, theme.current(self.settings))

    def test_unknown_value_falls_back_to_light(self):
        self.settings.setValue(theme.MODE_KEY, 'rainbow')
        self.assertEqual(theme.LIGHT, theme.current(self.settings))

    def test_button_label_offers_the_other_mode(self):
        # 深色时按钮应当写着"浅色"，反之亦然
        self.assertEqual('深色', theme.label(theme.LIGHT))
        self.assertEqual('浅色', theme.label(theme.DARK))


if __name__ == '__main__':
    unittest.main()
