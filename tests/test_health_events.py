import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox

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


class PatrolTests(unittest.TestCase):
    """一键巡检：点一下按钮必须真的有反馈（之前结果写进了隐藏标签）。"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def window_with(self, *ips):
        window = make_window(self)
        requested = []
        window._patrol_requested = requested
        window.thumbnails.request = lambda device: requested.append(device.ip)
        for ip in ips:
            device = Device(ip)
            window.add_device(device)        # 进设备列表：巡检按 ip 在 self.devices 里找
            window.wall.add_device(device)   # 同时摆到监控墙上
        return window

    def test_clicking_patrol_refreshes_every_camera_and_reports(self):
        window = self.window_with('10.0.0.1', '10.0.0.2')
        results = []
        window.wall.patrol_finished.connect(results.append)

        window.wall.check_action.trigger()

        self.assertEqual(['10.0.0.1', '10.0.0.2'], window._patrol_requested)
        self.assertEqual(1, len(results), '点击后必须给出汇总')
        self.assertIn('巡检 2 路', results[0])
        self.assertIn('未播放 2 路', results[0])

    def test_an_alerting_camera_is_listed_as_abnormal(self):
        window = self.window_with('10.0.0.1', '10.0.0.2')
        window.wall.tiles[0].show_alert('画面可能全黑：请检查镜头')
        results = []
        window.wall.patrol_finished.connect(results.append)

        window.wall.start_patrol()

        self.assertIn('异常 1 路', results[0])
        self.assertIn('10.0.0.1', results[0])

    def test_the_result_reaches_the_window_status_bar(self):
        window = self.window_with('10.0.0.3')
        window.show_patrol_result('巡检 1 路：正常 0 路，异常 0 路，未播放 1 路\n未播放：10.0.0.3')
        self.assertIn('巡检 1 路', window.status.text())

    def test_an_empty_wall_says_so(self):
        window = make_window(self)
        results = []
        window.wall.patrol_finished.connect(results.append)
        window.wall.start_patrol()
        self.assertIn('还没有相机', results[0])


class PatrolScreenshotTests(unittest.TestCase):
    """巡检截图：首次点击提示设置位置，图片统一进当天的日期文件夹。"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)

    def day_folder(self):
        return Path(self.folder) / datetime.now().strftime('%Y-%m-%d')

    def window_with_shot(self, *ips):
        window = make_window(self)
        window.thumbnails.request = lambda *args, **kwargs: None
        for ip in ips:
            device = Device(ip)
            window.add_device(device)
            window.wall.add_device(device)
        for tile in window.wall.tiles:
            tile.player.surface.current_image = lambda color=0x336699: picture(color=color)
        return window

    def test_configured_folder_gets_a_dated_subfolder(self):
        window = self.window_with_shot('10.0.0.1', '10.0.0.2')
        window.device_names.settings.setValue('monitor/patrol_folder', self.folder)

        window.wall.screenshot_action.trigger()

        files = sorted(path.name for path in self.day_folder().glob('*.jpg'))
        self.assertEqual(2, len(files), '每路各存一张')
        self.assertTrue(all(name.startswith('10_0_0_') for name in files))
        self.assertIn('保存 2 张', window.status.text())

    def test_screenshot_is_named_after_the_camera(self):
        window = self.window_with_shot('10.0.0.1')
        window.device_names.save('10.0.0.1', '大门口')
        window.device_names.settings.setValue('monitor/patrol_folder', self.folder)

        window.capture_patrol_screenshots()

        names = [path.name for path in self.day_folder().glob('*.jpg')]
        self.assertEqual(1, len(names))
        self.assertTrue(names[0].startswith('大门口_'), names)

    def test_a_camera_without_a_name_falls_back_to_its_ip(self):
        window = self.window_with_shot('10.0.0.9')
        window.device_names.settings.setValue('monitor/patrol_folder', self.folder)

        window.capture_patrol_screenshots()

        names = [path.name for path in self.day_folder().glob('*.jpg')]
        self.assertEqual(1, len(names))
        self.assertTrue(names[0].startswith('10_0_0_9_'), names)

    def test_a_name_with_illegal_characters_is_cleaned_up(self):
        window = self.window_with_shot('10.0.0.1')
        window.device_names.save('10.0.0.1', '东/西 门: 1')
        window.device_names.settings.setValue('monitor/patrol_folder', self.folder)

        window.capture_patrol_screenshots()

        name = next(iter(self.day_folder().glob('*.jpg'))).name
        self.assertNotIn('/', name)
        self.assertNotIn(':', name)
        self.assertTrue(name.startswith('东_西_门_1_'), name)

    def test_a_second_capture_in_the_same_second_does_not_overwrite(self):
        window = self.window_with_shot('10.0.0.1')
        window.device_names.save('10.0.0.1', '大门口')
        window.device_names.settings.setValue('monitor/patrol_folder', self.folder)

        window.capture_patrol_screenshots()
        window.capture_patrol_screenshots()

        names = [path.name for path in self.day_folder().glob('*.jpg')]
        self.assertEqual(2, len(names), '两次截图都要留下，不能互相覆盖')

    def test_the_first_click_asks_where_to_save_and_can_be_cancelled(self):
        window = self.window_with_shot('10.0.0.1')

        with patch('camera_monitor.app.QMessageBox.question',
                   return_value=QMessageBox.StandardButton.No):
            window.capture_patrol_screenshots()

        self.assertEqual('', window.patrol_folder(), '取消后不应记住任何目录')
        self.assertFalse(self.day_folder().exists())

    def test_picking_a_folder_on_the_first_click_then_captures(self):
        window = self.window_with_shot('10.0.0.1')

        with patch('camera_monitor.app.QMessageBox.question',
                   return_value=QMessageBox.StandardButton.Yes), \
                patch('camera_monitor.app.QFileDialog.getExistingDirectory',
                      return_value=self.folder):
            window.capture_patrol_screenshots()

        self.assertEqual(self.folder, window.patrol_folder())
        self.assertEqual(1, len(list(self.day_folder().glob('*.jpg'))))

    def test_a_camera_without_any_picture_is_reported_not_saved(self):
        window = self.window_with_shot('10.0.0.1')
        window.wall.tiles[0].player.surface.current_image = lambda: None
        window.device_names.settings.setValue('monitor/patrol_folder', self.folder)

        window.capture_patrol_screenshots()

        self.assertIn('无画面', window.status.text())
        self.assertEqual([], list(self.day_folder().glob('*.jpg')))


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
