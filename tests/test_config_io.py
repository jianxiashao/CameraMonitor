import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QSettings

from camera_monitor.config_io import ConfigError, apply_config, export_config, load_config
from camera_monitor.connection_options import ConnectionOptions
from camera_monitor.device_names import DeviceNames
from camera_monitor.discovery import Device


class ConfigIoTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)

    def settings(self, name):
        return QSettings(str(self.base / name), QSettings.Format.IniFormat)

    def test_export_never_contains_passwords(self):
        names, options = DeviceNames(self.settings('names.ini')), ConnectionOptions(self.settings('conn.ini'))
        names.save('10.0.0.1', '大门')
        options.save_transport('10.0.0.1', 'udp')
        path = export_config(self.base / 'conf', names, options,
                             [Device('10.0.0.1', name='Front', model='IPC')], capacity=9,
                             slots=['10.0.0.1', '', ''])
        document = json.loads(Path(path).read_text(encoding='utf-8'))
        self.assertEqual('camera-monitor-config', document['format'])
        self.assertEqual(9, document['layout']['capacity'])
        self.assertEqual(['10.0.0.1', '', ''], document['layout']['slots'])
        camera = document['cameras'][0]
        self.assertEqual('大门', camera['name'])
        self.assertEqual('udp', camera['transport'])
        self.assertNotIn('password', json.dumps(document, ensure_ascii=False).lower())

    def test_round_trip_applies_to_a_fresh_machine(self):
        names, options = DeviceNames(self.settings('a-names.ini')), ConnectionOptions(self.settings('a-conn.ini'))
        names.save('10.0.0.2', '厨房')
        names.save_appearance('10.0.0.2', '#ffff00', 'bottom-right')
        options.save_transport('10.0.0.2', 'udp')
        path = export_config(self.base / 'conf', names, options, [Device('10.0.0.2')], capacity=4,
                             slots=['10.0.0.2'])

        other_names = DeviceNames(self.settings('b-names.ini'))
        other_options = ConnectionOptions(self.settings('b-conn.ini'))
        document = load_config(path)
        self.assertEqual(1, apply_config(document, other_names, other_options))

        self.assertEqual('厨房', other_names.get('10.0.0.2'))
        self.assertEqual(('#ffff00', 'bottom-right'), other_names.appearance('10.0.0.2'))
        self.assertEqual('udp', other_options.transport('10.0.0.2'))
        self.assertEqual(['10.0.0.2'], other_names.slot_order())

    def test_rejects_foreign_and_broken_files(self):
        broken = self.base / 'broken.json'
        broken.write_text('{not json', encoding='utf-8')
        foreign = self.base / 'foreign.json'
        foreign.write_text(json.dumps({'format': 'something-else'}), encoding='utf-8')
        empty = self.base / 'empty.json'
        empty.write_text(json.dumps({'format': 'camera-monitor-config', 'cameras': []}), encoding='utf-8')
        for path in (broken, foreign, empty, self.base / 'missing.json'):
            with self.assertRaises(ConfigError):
                load_config(str(path))


if __name__ == '__main__':
    unittest.main()
