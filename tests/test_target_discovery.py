import socket
import threading
import unittest
from camera_monitor.discovery import Interface, scan
from support import loopback_udp_available
from test_discovery import ONVIF


class TargetDiscoveryTests(unittest.TestCase):
    def test_unicast_onvif_finds_camera_without_multicast(self):
        if not loopback_udp_available():
            self.skipTest('本机不允许回环 UDP，跳过真实网络用例')
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 3702 在部分 Windows 上被系统保留，测试用临时端口，别和环境较劲
        server.bind(('127.0.0.1', 0))
        port = server.getsockname()[1]
        server.settimeout(1)
        errors = []
        def reply():
            try:
                _, address = server.recvfrom(8192)
                server.sendto(ONVIF, address)
            except Exception as exc:
                errors.append(exc)
        thread = threading.Thread(target=reply)
        thread.start()
        try:
            found = scan([Interface('test', '127.0.0.1', '127.255.255.255')],
                         target_ip='127.0.0.1', duration=0.2, onvif_port=port)
            self.assertEqual([d.ip for d in found], ['127.0.0.1'])
            self.assertEqual(found[0].protocols, ['ONVIF'])
        finally:
            thread.join(2)
            server.close()
        self.assertEqual(errors, [])

    def test_invalid_target_rejected_before_network_access(self):
        for ip in ('bad', 'http://192.168.2.216', '::1', '0.0.0.0', '239.1.2.3', '255.255.255.255'):
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                scan([], target_ip=ip, duration=0)

    def test_timeout_does_not_invent_a_device(self):
        self.assertEqual(scan([Interface('test', '127.0.0.1', '127.255.255.255')],
                              target_ip='127.0.0.1', duration=0.03), [])
