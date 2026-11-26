"""ONVIF 云台控制：按住方向键持续移动，松开停止；支持预置位。"""
from __future__ import annotations

import queue
import threading

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QVBoxLayout)

from .streams import OnvifClient

# 关闭窗口时还没退出的云台线程先摘出来，等它自己结束；QThread 运行中被销毁会 abort
_ORPHANS = set()


class PtzWorker(QThread):
    status = Signal(str)
    failed = Signal(str)
    presets_loaded = Signal(list)

    def __init__(self, device, username, password, parent=None):
        super().__init__(parent)
        self.device, self.username, self.password = device, username, password
        self.commands = queue.Queue()
        self.cancel = threading.Event()

    def send(self, command, *args):
        if not self.cancel.is_set():
            self.commands.put((command, args))

    def shutdown(self):
        self.cancel.set()
        self.commands.put(('quit', ()))

    def run(self):
        client = None
        try:
            client = OnvifClient(self.device, self.username, self.password, self.cancel)
            context = client.ptz_context()
            self.status.emit('云台已就绪')
            try:
                self.presets_loaded.emit(client.ptz_presets(context))
            except Exception:
                self.presets_loaded.emit([])
            while not self.cancel.is_set():
                try:
                    command, args = self.commands.get(timeout=0.2)
                except queue.Empty:
                    continue
                if command == 'quit':
                    break
                try:
                    if command == 'move':
                        client.ptz_move(context, *args)
                    elif command == 'halt':
                        client.ptz_stop(context)
                    elif command == 'goto':
                        client.ptz_goto_preset(context, args[0])
                except Exception:
                    # 通信失败不弹一堆框；现场看状态栏即可
                    self.status.emit('云台指令没有发出去，请检查相机 ONVIF 权限')
        except Exception:
            self.failed.emit('连不上云台：相机可能不支持 ONVIF PTZ，或账号没有云台权限。')
        finally:
            if client:
                client.close()
            self.password = ''


class PtzDialog(QDialog):
    DIRECTIONS = {
        '左上': (-0.7, 0.7), '上': (0, 1), '右上': (0.7, 0.7),
        '左': (-1, 0), '停止': (0, 0), '右': (1, 0),
        '左下': (-0.7, -0.7), '下': (0, -1), '右下': (0.7, -0.7),
    }

    def __init__(self, device, username, password, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'云台控制 · {device.ip}')
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        self.status = QLabel('正在连接云台…')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        grid = QGridLayout()
        for index, (label, (x, y)) in enumerate(self.DIRECTIONS.items()):
            button = QPushButton(label)
            button.setMinimumSize(72, 44)
            if label == '停止':
                button.clicked.connect(self.halt)
            else:
                button.pressed.connect(lambda x=x, y=y: self.worker.send('move', x, y, 0))
                button.released.connect(self.halt)
            grid.addWidget(button, index // 3, index % 3)
        layout.addLayout(grid)

        zoom = QHBoxLayout()
        self.zoom_in = QPushButton('放大')
        self.zoom_out = QPushButton('缩小')
        self.zoom_in.pressed.connect(lambda: self.worker.send('move', 0, 0, 0.6))
        self.zoom_out.pressed.connect(lambda: self.worker.send('move', 0, 0, -0.6))
        self.zoom_in.released.connect(self.halt)
        self.zoom_out.released.connect(self.halt)
        zoom.addWidget(self.zoom_in)
        zoom.addWidget(self.zoom_out)
        layout.addLayout(zoom)

        preset_row = QHBoxLayout()
        self.presets = QComboBox()
        self.presets.addItem('（暂无预置位）', '')
        self.goto_button = QPushButton('调用预置位')
        self.goto_button.clicked.connect(self.goto_preset)
        preset_row.addWidget(self.presets, 1)
        preset_row.addWidget(self.goto_button)
        layout.addLayout(preset_row)

        close = QPushButton('关闭')
        close.clicked.connect(self.close)
        layout.addWidget(close)

        self.worker = PtzWorker(device, username, password, self)
        self.worker.status.connect(self.status.setText)
        self.worker.failed.connect(self.failed)
        self.worker.presets_loaded.connect(self.load_presets)
        self.worker.start()

    def halt(self):
        self.worker.send('halt')

    def failed(self, message):
        self.status.setText(message)
        self.zoom_in.setEnabled(False)
        self.zoom_out.setEnabled(False)
        self.goto_button.setEnabled(False)

    def load_presets(self, presets):
        self.presets.clear()
        if not presets:
            self.presets.addItem('（暂无预置位）', '')
            self.goto_button.setEnabled(False)
            return
        for token, name in presets:
            self.presets.addItem(name, token)
        self.goto_button.setEnabled(True)

    def goto_preset(self):
        token = self.presets.currentData()
        if token:
            self.worker.send('goto', token)

    def closeEvent(self, event):
        self.worker.shutdown()
        if not self.worker.wait(3000):
            worker = self.worker
            worker.setParent(None)
            _ORPHANS.add(worker)
            worker.finished.connect(lambda: (_ORPHANS.discard(worker), worker.deleteLater()))
            if worker.isFinished():
                _ORPHANS.discard(worker)
                worker.deleteLater()
        super().closeEvent(event)
