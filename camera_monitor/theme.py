"""浅色 / 深色主题。

夜间值守时白色背景太刺眼，所以给一个深色皮肤。这里只管"整体配色"：
监控墙本身一直是深色（画面区域），不受影响。

选择存在 QSettings 里，键 `ui/theme`，下次启动沿用。
"""
from PySide6.QtCore import QSettings

MODE_KEY = 'ui/theme'
LIGHT = 'light'
DARK = 'dark'
DEFAULT_MODE = LIGHT

ORGANIZATION = 'CameraMonitor'
APPLICATION = 'CameraMonitor'

DARK_QSS = """
QWidget { background: #131a24; color: #dbe4ef; }
QMainWindow, QDialog { background: #131a24; }
QLabel { background: transparent; }
QPushButton { background: #243044; color: #dbe4ef; border: 1px solid #33425a; border-radius: 4px; padding: 5px 10px; }
QPushButton:hover { background: #2d3b52; }
QPushButton:disabled { color: #6d7c90; border-color: #2a3547; }
QPushButton#primary { background: #2563eb; border-color: #2563eb; color: #ffffff; }
QPushButton#primary:hover { background: #1d4ed8; }
QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background: #1b2534; color: #dbe4ef; border: 1px solid #33425a; border-radius: 4px; padding: 3px;
}
QListWidget, QTreeWidget, QTableWidget {
    background: #16202d; color: #dbe4ef; alternate-background-color: #1b2534; border: 1px solid #2a3547;
}
QHeaderView::section { background: #1b2534; color: #a8b6c8; border: none; padding: 4px; }
QMenu { background: #1b2534; color: #dbe4ef; border: 1px solid #2a3547; }
QMenu::item:selected { background: #2d3b52; }
QScrollArea, QScrollBar { background: transparent; }
QProgressBar { background: #1b2534; border: none; }
QProgressBar::chunk { background: #2563eb; }
QFrame#cameraTile { background: #0b1119; }
"""

# 浅色就是 Qt 默认样式，不用额外写 QSS
LIGHT_QSS = ''


def settings_object():
    """与主程序共用一套设置：没显式传 settings 时用它。"""
    return QSettings(ORGANIZATION, APPLICATION)


def current(settings=None):
    settings = settings or settings_object()
    value = str(settings.value(MODE_KEY, DEFAULT_MODE) or DEFAULT_MODE)
    return value if value in (LIGHT, DARK) else DEFAULT_MODE


def set_mode(settings, mode):
    settings.setValue(MODE_KEY, DARK if mode == DARK else LIGHT)
    settings.sync()


def toggle(settings=None):
    """在浅色与深色之间切换，返回切换后的模式。"""
    settings = settings or settings_object()
    mode = DARK if current(settings) == LIGHT else LIGHT
    set_mode(settings, mode)
    return mode


def apply(app, mode):
    app.setStyleSheet(DARK_QSS if mode == DARK else LIGHT_QSS)


def label(mode):
    return '浅色' if mode == DARK else '深色'
