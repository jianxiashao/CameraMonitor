"""需要在后台跑的 ONVIF 小动作（目前是校准相机时间）。"""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from .streams import OnvifClient


class ClockSyncWorker(QThread):
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, device, username, password, parent=None):
        super().__init__(parent)
        self.device, self.username, self.password = device, username, password
        self.cancel = threading.Event()

    def run(self):
        client = None
        try:
            client = OnvifClient(self.device, self.username, self.password, self.cancel)
            client.set_system_date_and_time()
            if not self.cancel.is_set():
                self.done.emit('相机时间已校准到本机时间')
        except Exception as exc:
            if not self.cancel.is_set():
                # ONVIF 异常文本不含凭据，但统一用固定文案更稳妥
                text = str(exc) if exc.__class__.__module__ == 'camera_monitor.streams' else ''
                self.failed.emit(text or '校准失败：相机可能不支持修改时间，或账号没有权限。')
        finally:
            if client:
                client.close()
            self.password = ''
