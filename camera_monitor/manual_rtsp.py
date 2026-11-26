"""手动添加只支持 RTSP 的摄像头 / 录像机通道（如萤石、海康 NVR）。"""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout)

from .streams import strip_url_credentials


class ManualRtspDialog(QDialog):
    """只要名称和 RTSP 地址；地址里的账号密码会拆出来交给钥匙串。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('手动添加 RTSP 摄像头')
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(10)

        intro = QLabel('适用于只开放 RTSP、不响应 ONVIF / SADP 的摄像头，或海康 NVR 的某个通道。')
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.name = QLineEdit()
        self.name.setPlaceholderText('显示名称，例如：大门 / 萤石客厅 / NVR 通道 3')
        layout.addWidget(self.name)
        self.url = QLineEdit()
        self.url.setPlaceholderText('rtsp://用户:密码@192.168.1.64:554/Streaming/Channels/101')
        layout.addWidget(self.url)

        hint = QLabel(
            '示例：\n'
            '海康 / 萤石：rtsp://用户:验证码@IP:554/Streaming/Channels/101（子码流 102，通道 2 用 201/202）\n'
            '大华：rtsp://用户:密码@IP:554/cam/realmonitor?channel=1&subtype=0\n'
            '地址里不写账号密码也可以，下一步在连接设置里填。')
        hint.setObjectName('muted')
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.error = QLabel()
        self.error.setObjectName('aboutError')
        self.error.setStyleSheet('color:#c0392b;')
        self.error.setWordWrap(True)
        layout.addWidget(self.error)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton('取消')
        cancel.clicked.connect(self.reject)
        add = QPushButton('添加')
        add.setObjectName('primary')
        add.clicked.connect(self.validate_and_accept)
        buttons.addWidget(cancel)
        buttons.addWidget(add)
        layout.addLayout(buttons)
        self.url.setFocus()
        self._values = {}

    def validate_and_accept(self):
        value = self.url.text().strip()
        try:
            parts = urlsplit(value)
            if parts.scheme not in ('rtsp', 'rtsps') or not parts.hostname:
                raise ValueError()
            _ = parts.port
        except ValueError:
            self.error.setText('请输入有效的 RTSP 地址，例如 rtsp://192.168.1.64:554/...')
            return
        self.error.clear()
        self._values = self.parse(value)
        super().accept()

    @staticmethod
    def parse(value):
        parts = urlsplit(value.strip())
        host = parts.hostname or ''
        username = parts.username or ''
        password = parts.password or ''
        clean = strip_url_credentials(urlunsplit(parts))
        return {
            'url': clean,
            'host': host,
            'username': username,
            'password': password,
        }

    def values(self):
        return self.name.text().strip(), self._values


__all__ = ['ManualRtspDialog']
