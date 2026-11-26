import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest

from PySide6.QtWidgets import QApplication, QDialog

from camera_monitor.manual_rtsp import ManualRtspDialog


class ManualRtspTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_address_is_split_into_host_and_credentials(self):
        dialog = ManualRtspDialog()
        self.addCleanup(dialog.deleteLater)
        dialog.name.setText('大门')
        dialog.url.setText('rtsp://admin:secret@10.0.0.5:554/Streaming/Channels/101')
        dialog.validate_and_accept()

        self.assertEqual(QDialog.DialogCode.Accepted, dialog.result())
        name, values = dialog.values()
        self.assertEqual('大门', name)
        self.assertEqual('10.0.0.5', values['host'])
        self.assertEqual('admin', values['username'])
        self.assertEqual('secret', values['password'])
        self.assertEqual('rtsp://10.0.0.5:554/Streaming/Channels/101', values['url'])
        self.assertNotIn('secret', values['url'])

    def test_non_rtsp_address_is_rejected(self):
        dialog = ManualRtspDialog()
        self.addCleanup(dialog.deleteLater)
        dialog.url.setText('http://10.0.0.5/live')
        dialog.validate_and_accept()
        self.assertEqual(QDialog.DialogCode.Rejected, dialog.result())
        self.assertTrue(dialog.error.text())

    def test_rtsps_and_hostnames_are_accepted(self):
        values = ManualRtspDialog.parse('rtsps://camera.local:322/live')
        self.assertEqual('camera.local', values['host'])
        self.assertEqual('rtsps://camera.local:322/live', values['url'])


if __name__ == '__main__':
    unittest.main()
