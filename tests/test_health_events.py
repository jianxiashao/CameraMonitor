import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from camera_monitor.cloud_channel import CloudChannel
from camera_monitor.discovery import Device
from camera_monitor.recorder import RecorderPool
from support import make_window


def picture(width=64, height=48, color=0x3366cc):
    image = QImage(width, height, QImage.Format.Format_RGB888)
    image.fill(color)
    return image


class HealthSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_health_reports_each_camera(self):
        window = make_window(self)
        window.wall.add_device(Device('10.0.0.1'))
        tile = window.wall.tiles[0]
        tile.show_latency(1.7)
        tile.show_alert('画面可能全黑')

        health = window.camera_health()
        self.assertEqual(1, len(health['cameras']))
        camera = health['cameras'][0]
        self.assertEqual('10.0.0.1', camera['ip'])
        self.assertEqual(1.7, camera['behind'])
        self.assertIn('全黑', camera['alert'])
        self.assertIn('reconnects', camera)
        # 机器负载拿不到也不影响整体结构
        self.assertIn('cameras', health)


class AlertEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_events_queue_while_offline_and_flush_when_back(self):
        window = make_window(self)
        window.cloud.token = 'cm1.test-token'
        window.channel.online = False
        window.wall.add_device(Device('10.0.0.9'))
        window.wall.tiles[0].show_alert('画面可能全黑')

        self.assertEqual(1, len(window.pending_events), '离线时事件应当排队')

        sent = []
        window.channel.send = lambda payload: sent.append(payload) or True
        window.channel.online = True
        window.flush_pending_events()

        self.assertEqual([], window.pending_events)
        self.assertEqual('camera_alert', sent[0]['event'])
        self.assertEqual('10.0.0.9', sent[0]['ip'])

    def test_a_standalone_machine_never_posts_events(self):
        window = make_window(self)
        window.cloud.token = ''
        window.wall.add_device(Device('10.0.0.8'))
        window.wall.tiles[0].show_alert('画面可能全黑')
        self.assertEqual([], window.pending_events, '没登录云端就不该往外发')

    def test_queue_is_capped_so_it_cannot_grow_forever(self):
        window = make_window(self)
        window.cloud.token = 'cm1.test-token'
        window.channel.online = False
        for index in range(25):
            window.pending_events.append({'type': 'event', 'ip': f'10.0.1.{index}'})
            del window.pending_events[:-20]
        self.assertEqual(20, len(window.pending_events))


class HeartbeatHealthTests(unittest.TestCase):
    def test_ping_carries_the_health_snapshot(self):
        sent = []
        channel = CloudChannel('ws://127.0.0.1/ws', lambda: None,
                               health=lambda: {'cameras': [], 'cpu': 12.5},
                               clock=lambda: 0.0)
        channel.send = lambda payload: sent.append(payload) or True
        channel.last_heard = 0.0
        channel._beat()

        self.assertEqual(1, len(sent))
        self.assertEqual('ping', sent[0]['type'])
        self.assertEqual(12.5, sent[0]['health']['cpu'])

    def test_a_broken_health_callback_does_not_break_the_heartbeat(self):
        def broken():
            raise RuntimeError('boom')

        sent = []
        channel = CloudChannel('ws://127.0.0.1/ws', lambda: None, health=broken, clock=lambda: 0.0)
        channel.send = lambda payload: sent.append(payload) or True
        channel.last_heard = 0.0
        channel._beat()

        self.assertEqual('ping', sent[0]['type'])
        self.assertNotIn('health', sent[0], '取不到状态也要照常发心跳')


class FreezeSlicesTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)

    def test_alert_freezes_the_recent_segments(self):
        pool = RecorderPool(folder=str(self.base), enabled=True)
        self.addCleanup(pool.close)
        for _ in range(3):
            pool.add('10.0.0.5', picture())
        self.assertEqual(1, len(pool.segments('10.0.0.5')))

        saved = pool.freeze('10.0.0.5')
        self.assertEqual(1, len(saved), '应当把最近一段复制到事件目录')
        self.assertTrue(Path(saved[0]).exists())
        self.assertIn('camera-monitor-events', saved[0])
        # 原环形缓冲还在，回看不受影响
        self.assertTrue(pool.segments('10.0.0.5'))

    def test_freezing_an_unknown_camera_is_harmless(self):
        pool = RecorderPool(folder=str(self.base), enabled=True)
        self.addCleanup(pool.close)
        self.assertEqual([], pool.freeze('10.0.0.77'))


if __name__ == '__main__':
    unittest.main()
