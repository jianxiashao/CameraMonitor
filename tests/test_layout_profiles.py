import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QSettings

from camera_monitor import layout_profiles


class LayoutProfileTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.settings = QSettings(str(Path(self.folder.name) / 'layout.ini'),
                                  QSettings.Format.IniFormat)

    def test_save_load_and_delete(self):
        layout_profiles.save_profile(self.settings, '夜班', {
            'capacity': 4, 'slots': ['10.0.0.1', '10.0.0.2'], 'columns': {'4': 2},
            'fill_width': True, 'organization': '仓库'})
        profiles = layout_profiles.load_all(self.settings)
        self.assertEqual(['10.0.0.1', '10.0.0.2'], profiles['夜班']['slots'])
        self.assertTrue(profiles['夜班']['fill_width'])

        layout_profiles.delete_profile(self.settings, '夜班')
        self.assertEqual({}, layout_profiles.load_all(self.settings))

    def test_invalid_documents_are_rejected(self):
        with self.assertRaises(ValueError):
            layout_profiles.save_profile(self.settings, '', {'capacity': 4, 'slots': []})
        with self.assertRaises(ValueError):
            layout_profiles.save_profile(self.settings, '坏方案', {'slots': 'not-a-list'})


if __name__ == '__main__':
    unittest.main()
