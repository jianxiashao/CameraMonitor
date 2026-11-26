import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest

from PySide6.QtWidgets import QApplication

from camera_monitor import __version__
from camera_monitor.about_dialog import AboutDialog


class AboutDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_shows_the_current_version_and_environment(self):
        dialog = AboutDialog()
        self.addCleanup(dialog.deleteLater)
        self.assertIn(__version__, dialog.version.text())
        self.assertIn('Qt', dialog.environment.text())
        self.assertIn('Python', dialog.environment.text())
        self.assertIn(__version__, dialog.info_text())

    def test_copy_info_puts_version_on_the_clipboard(self):
        dialog = AboutDialog()
        self.addCleanup(dialog.deleteLater)
        dialog.copy_info()
        self.assertIn(__version__, QApplication.clipboard().text())


if __name__ == '__main__':
    unittest.main()
