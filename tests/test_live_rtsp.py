"""真实 RTSP 端到端：用 ffmpeg 起一路本地流，让解码线程真的解出画面。

单元测试里的 Decoder 都是拿本地文件冒充流，这条路径（RTSP 握手、探测、
首帧、时间戳）只有真流才能覆盖。没装 ffmpeg 的机器自动跳过；
`.github/workflows/live-rtsp.yml` 在云端手动跑这一条。
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import shutil
import socket
import subprocess
import time
import unittest

from PySide6.QtWidgets import QApplication

from camera_monitor.playback import Decoder

FFMPEG = shutil.which('ffmpeg')


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@unittest.skipUnless(FFMPEG, '需要 ffmpeg 才能起本地 RTSP 流')
class LiveRtspTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_decoder_plays_a_real_rtsp_stream(self):
        port = free_port()
        url = f'rtsp://127.0.0.1:{port}/live'
        server = subprocess.Popen(
            [FFMPEG, '-loglevel', 'error', '-re', '-f', 'lavfi',
             '-i', 'testsrc=size=320x240:rate=10', '-c:v', 'mpeg4', '-q:v', '5',
             '-f', 'rtsp', '-rtsp_flags', 'listen', url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        worker = None
        try:
            time.sleep(2.0)   # 等 ffmpeg 真正开始监听
            worker = Decoder(url, max_width=320)
            ready, errors = [], []
            worker.ready.connect(ready.append)
            worker.error.connect(errors.append)
            worker.start()
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and not ready and not errors:
                self.app.processEvents()
                time.sleep(0.05)
            self.assertEqual([], errors, '真实 RTSP 流不该报错')
            self.assertTrue(ready, '应当从真实 RTSP 流里拿到第一帧')
            self.assertIn('320', ready[0])
        finally:
            if worker is not None:
                worker.cancel.set()
                worker.wait(5000)
            server.terminate()
            try:
                server.wait(5)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == '__main__':
    unittest.main()
