"""关于对话框：版本、运行环境、数据目录和项目链接。"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QUrl, qVersion
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QLabel,
                               QPushButton, QVBoxLayout)

from . import __version__

PROJECT_URL = 'https://github.com/jianxiashao/CameraMonitor'
RELEASES_URL = 'https://github.com/jianxiashao/CameraMonitor/releases/latest'


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('aboutDialog')
        self.setWindowTitle('关于 Camera Monitor')
        self.setWindowIcon(QIcon(str(Path(__file__).parent / 'assets' / 'app-icon.png')))
        self.setMinimumWidth(520)
        self.setMaximumWidth(620)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        card = QFrame()
        card.setObjectName('aboutCard')
        outer.addWidget(card)
        box = QVBoxLayout(card)
        box.setContentsMargins(26, 24, 26, 22)
        box.setSpacing(12)

        heading = QHBoxLayout()
        heading.setSpacing(14)
        icon = QLabel()
        pixmap = QIcon(str(Path(__file__).parent / 'assets' / 'app-icon.png')).pixmap(64, 64)
        icon.setPixmap(pixmap)
        icon.setFixedSize(64, 64)
        icon.setObjectName('aboutLogo')
        heading.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel('Camera Monitor')
        title.setObjectName('aboutTitle')
        self.subtitle = QLabel('内网监控中心 · 轻量 RTSP 监控墙')
        self.subtitle.setObjectName('aboutSubtitle')
        self.version = QLabel(f'版本 {__version__}')
        self.version.setObjectName('aboutVersion')
        titles.addWidget(title)
        titles.addWidget(self.subtitle)
        titles.addWidget(self.version)
        heading.addLayout(titles, 1)
        box.addLayout(heading)

        self.description = QLabel(
            '自动发现局域网摄像头，在一个窗口里查看多路实时画面。\n'
            '支持 ONVIF、大华 DHIP、海康 SADP 发现，也可手动添加 RTSP 地址；'
            '云端配置同步可选，不登录云端时完全在本机运行。')
        self.description.setObjectName('aboutText')
        self.description.setWordWrap(True)
        box.addWidget(self.description)

        self.environment = QLabel(self.environment_text())
        self.environment.setObjectName('aboutMeta')
        self.environment.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box.addWidget(self.environment)

        self.data_path = QLabel(f'数据目录：{self.data_folder()}')
        self.data_path.setObjectName('aboutMeta')
        self.data_path.setWordWrap(True)
        self.data_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box.addWidget(self.data_path)

        links = QHBoxLayout()
        links.setSpacing(8)
        for text, url in (('项目主页', PROJECT_URL), ('下载最新版', RELEASES_URL)):
            button = QPushButton(text)
            button.setObjectName('aboutLink')
            button.clicked.connect(lambda checked=False, target=url: QDesktopServices.openUrl(QUrl(target)))
            links.addWidget(button)
        links.addStretch(1)
        copy = QPushButton('复制版本信息')
        copy.clicked.connect(self.copy_info)
        links.addWidget(copy)
        box.addLayout(links)

        footer = QHBoxLayout()
        note = QLabel('摄像头凭据保存在系统安全存储中，诊断包不包含密码和令牌。')
        note.setObjectName('aboutMeta')
        note.setWordWrap(True)
        footer.addWidget(note, 1)
        close = QPushButton('关闭')
        close.setObjectName('primary')
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        box.addLayout(footer)

    def environment_text(self):
        try:
            python = platform.python_version()
        except Exception:
            python = sys.version.split()[0]
        return f'Qt {qVersion()} · Python {python} · {platform.system()} {platform.release()} · {platform.machine()}'

    def data_folder(self):
        folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        return folder or '（无法读取）'

    def info_text(self):
        return (f'Camera Monitor {__version__}\n'
                f'{self.environment.text()}\n'
                f'数据目录：{self.data_folder()}\n'
                f'项目主页：{PROJECT_URL}')

    def copy_info(self):
        QApplication.clipboard().setText(self.info_text())
