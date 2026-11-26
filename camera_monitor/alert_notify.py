"""把画面异常推到现场自己的 Webhook（企业微信/钉钉/自建服务都能接）。"""
from __future__ import annotations

import logging
import time

import requests
from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger(__name__)
TIMEOUT = (3.0, 5.0)
_ORPHANS = set()


class WebhookCall(QThread):
    done = Signal(bool, str)

    def __init__(self, url, payload, parent=None):
        super().__init__(parent)
        self.url, self.payload = url, payload

    def run(self):
        try:
            response = requests.post(self.url, json=self.payload, timeout=TIMEOUT,
                                     allow_redirects=False)
            ok = 200 <= response.status_code < 300
            self.done.emit(ok, '' if ok else f'HTTP {response.status_code}')
        except requests.RequestException as exc:
            # URL 里可能带 key，不把异常原文带出去
            self.done.emit(False, type(exc).__name__)


class WebhookNotifier(QObject):
    """一次只发一条；失败只记日志，不影响监控。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None

    def send(self, url, ip, message):
        if not url or self.worker is not None:
            return False
        text = f'摄像头 {ip}：{message}'
        payload = {'type': 'camera_alert', 'ip': ip, 'message': message,
                   'text': text, 'content': text, 'at': int(time.time())}
        worker = WebhookCall(url, payload, self)
        self.worker = worker
        worker.done.connect(self._finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        return True

    def _finished(self, ok, error):
        if not ok:
            logger.warning('告警 Webhook 发送失败：%s', error)
        self.worker = None

    def stop(self):
        """退出时最多等几秒；等不到就摘掉父对象，别让 QThread 在运行中被销毁。"""
        worker = self.worker
        if worker is None or worker.wait(5000):
            return
        self.worker = None
        worker.setParent(None)
        _ORPHANS.add(worker)
        worker.finished.connect(lambda: (_ORPHANS.discard(worker), worker.deleteLater()))
