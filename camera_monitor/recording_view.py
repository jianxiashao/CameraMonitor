"""回看最近几分钟的缩时画面：一个只播放、不带控制的简单窗口。"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .recorder import frames_of

PLAY_INTERVAL_MS = 1000


class RecordingViewer(QDialog):
    """按时间顺序播放这台相机的环形录像（1 帧/秒的缩时画面）。"""

    def __init__(self, title, segments, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'回看 · {title}')
        self.resize(880, 560)
        self.segments = list(segments)
        self.frames = frames_of(self.segments)
        self.playing = True
        self.shown = 0

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
        self.play_button = QPushButton('暂停')
        self.play_button.clicked.connect(self.toggle_play)
        close = QPushButton('关闭')
        close.clicked.connect(self.close)
        buttons.addWidget(self.play_button)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)

        if not self.segments:
            self.hint.setText('这台相机还没有可回看的画面')
            self.play_button.setEnabled(False)
        else:
            self.hint.setText(f'最近 {len(self.segments)} 段 · 每秒一帧')
            self.timer = QTimer(self)
            self.timer.setInterval(PLAY_INTERVAL_MS)
            self.timer.timeout.connect(self.next_frame)
            self.timer.start()
            self.next_frame()

    def toggle_play(self):
        self.playing = not self.playing
        if self.playing:
            self.timer.start()
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
        self.hint.setText(f'第 {self.shown} 帧 · 最近 {len(self.segments)} 段')

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()
        super().closeEvent(event)
