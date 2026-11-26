import unittest

from camera_monitor import cloud_state
from camera_monitor.diagnostics import redact_text
from camera_monitor.discovery import Device
from camera_monitor.streams import strip_url_credentials


class UrlCredentialTests(unittest.TestCase):
    def test_manual_url_credentials_are_removed_before_sync(self):
        entry = cloud_state.camera_entry(
            Device('10.0.0.1'), slot_index=0,
            manual_url='rtsp://admin:secret@10.0.0.1:554/live')
        self.assertEqual('rtsp://10.0.0.1:554/live', entry['manual_url'])

    def test_cacheable_strips_credentials_from_old_snapshots(self):
        snapshot = {'cameras': [{'ip': '10.0.0.1',
                                 'manual_url': 'rtsp://admin:secret@10.0.0.1/live'}]}
        cached = cloud_state.cacheable(snapshot)
        self.assertEqual('rtsp://10.0.0.1/live', cached['cameras'][0]['manual_url'])
        self.assertNotIn('secret', str(cached))

    def test_plain_urls_are_unchanged(self):
        self.assertEqual('rtsp://10.0.0.1/live', strip_url_credentials('rtsp://10.0.0.1/live'))
        self.assertEqual('', strip_url_credentials('http://[broken'))

    def test_diagnostics_scrubs_url_credentials_in_text_and_values(self):
        self.assertEqual('rtsp://***@cam/live',
                         redact_text('rtsp://admin:secret@cam/live'))


class FingerprintTests(unittest.TestCase):
    def test_fingerprint_is_a_hash_and_does_not_expose_passwords(self):
        value = cloud_state.config_fingerprint(
            {'capacity': 4},
            [{'ip': '10.0.0.1', 'slot_index': 0, 'password': 'secret', 'username': 'admin'}])
        self.assertEqual(64, len(value))
        self.assertNotIn('secret', value)


if __name__ == '__main__':
    unittest.main()
