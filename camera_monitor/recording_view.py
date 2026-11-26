"""回看最近几分钟的缩时画面：一个只播放、不带控制的简单窗口。"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout)

from .recorder import frames_of

PLAY_INTERVAL_MS = 1000


class RecordingViewer(QDialog):
    """按时间顺序播放这台相机的环形录像（1 帧/秒的缩时画面）。

    默认从最新的一段开始：点「回看」的人通常想看刚才发生了什么，而不是先等
    十分钟把最早的画面放一遍。需要完整过程时再点「从头播放」。
    """

    def __init__(self, title, segments, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'回看 · {title}')
        self.resize(880, 560)
        self.all_segments = list(segments)
        self.segments = self.all_segments[-1:] if self.all_segments else []
        self.frames = frames_of(self.segments)
        self.playing = True
        self.shown = 0
        self.speed = 1.0

        layout = QVBoxLayout(self)
        self.hint = QLabel()
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint)
        self.surface = QLabel()
        self.surface.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.surface.setStyleSheet('background:#101827;')
        self.surface.setMinimumSize(320, 180)
        layout.addWidget(self.surface, 1)

        buttons = QHBoxLayout()
        self.latest_button = QPushButton('最新')
        self.latest_button.setToolTip('只放最近一段，最快看到刚才的画面')
        self.latest_button.clicked.connect(self.play_latest)
        self.all_button = QPushButton('从头播放')
        self.all_button.clicked.connect(self.play_all)
        self.speed_choice = QComboBox()
        for label, value in (('1x', 1.0), ('2x', 2.0), ('4x', 4.0), ('8x', 8.0)):
            self.speed_choice.addItem(label, value)
        self.speed_choice.currentIndexChanged.connect(self.speed_changed)
        self.play_button = QPushButton('暂停')
        self.play_button.clicked.connect(self.toggle_play)
        close = QPushButton('关闭')
        close.clicked.connect(self.close)
        for widget in (self.latest_button, self.all_button, self.speed_choice,
                       self.play_button):
            buttons.addWidget(widget)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        if not self.segments:
            self.hint.setText('这台相机还没有可回看的画面')
            for widget in (self.latest_button, self.all_button, self.play_button,
                           self.speed_choice):
                widget.setEnabled(False)
        else:
            self.restart(self.segments)

    def restart(self, segments):
        self.segments = list(segments)
        self.frames = frames_of(self.segments)
        self.shown = 0
        self.hint.setText(f'最近 {len(self.segments)} 段 · 每秒一帧 · {self.speed:g}x')
        self.play_button.setEnabled(True)
        self.play_button.setText('暂停')
        self.playing = True
        self.timer.setInterval(max(30, int(PLAY_INTERVAL_MS / self.speed)))
        self.timer.start()
        self.next_frame()

    def play_latest(self):
        if self.all_segments:
            self.restart(self.all_segments[-1:])

    def play_all(self):
        if self.all_segments:
            self.restart(self.all_segments)

    def speed_changed(self, _index):
        try:
            self.speed = float(self.speed_choice.currentData() or 1.0)
        except (TypeError, ValueError):
            self.speed = 1.0
        if self.timer.isActive():
            self.timer.setInterval(max(30, int(PLAY_INTERVAL_MS / self.speed)))
        self.hint.setText(f'最近 {len(self.segments)} 段 · 每秒一帧 · {self.speed:g}x')

    def toggle_play(self):
        self.playing = not self.playing
        if self.playing:
            self.timer.start(max(30, int(PLAY_INTERVAL_MS / self.speed)))
            self.play_button.setText('暂停')
        else:
            self.timer.stop()
            self.play_button.setText('继续')

    def next_frame(self):
        """取下一帧显示；放完就停在最后一帧并切换按钮文字。"""
        try:
            image = next(self.frames)
        except StopIteration:
            self.timer.stop()
            self.play_button.setEnabled(False)
            self.play_button.setText('已放完')
            self.hint.setText('本轮录像已放完')
            return
        self.shown += 1
        self.surface.setPixmap(QPixmap.fromImage(image).scaled(
            self.surface.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation))
        self.hint.setText(f'第 {self.shown} 帧 · 最近 {len(self.segments)} 段 · {self.speed:g}x')

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)
