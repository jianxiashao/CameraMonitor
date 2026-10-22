"""浅色 / 深色主题。

界面配色只有一处来源：这里的两套 QSS。窗口不再自己 setStyleSheet，
否则会盖掉应用级样式（之前就踩过：切深色只改了菜单，主界面纹丝不动）。

选择存在 QSettings 的 `ui/theme`，下次启动沿用。
"""
from PySide6.QtCore import QSettings

MODE_KEY = 'ui/theme'
LIGHT = 'light'
DARK = 'dark'
DEFAULT_MODE = LIGHT

ORGANIZATION = 'CameraMonitor'
APPLICATION = 'CameraMonitor'

# 两套样式必须覆盖同一组控件，颜色之外的结构（圆角、内边距、字号）保持完全一致
_STRUCTURE = """
QLabel#title { font-size:24px; font-weight:700; }
QPushButton { border-radius:6px; padding:7px 10px; min-height:18px; }
QPushButton#primary { font-weight:600; }
QLineEdit, QSpinBox, QPlainTextEdit { border-radius:5px; padding:5px; }
QComboBox { border-radius:5px; padding:5px 8px; }
QMenu { border-radius:6px; padding:4px; }
QMenu::item { padding:6px 24px 6px 16px; border-radius:4px; }
QMenu::separator { height:1px; margin:4px 8px; }
QScrollArea { border:none; }
QFrame#settingsPanel { border-radius:8px; }
QSplitter::handle { width:1px; }
QPushButton#settingsTab { padding:4px; }
"""

LIGHT_QSS = """
QWidget { background:#f7f9fc; color:#203247; font-size:13px; }
QLabel#muted { color:#64748b; font-size:12px; }
QPushButton { background:white; border:1px solid #d7dfe9; }
QPushButton:hover { background:#eaf0fa; }
QPushButton:checked { background:#e3ecfb; border-color:#9db9ea; }
QPushButton#primary { background:#2463eb; color:white; border:1px solid #2463eb; }
QPushButton:disabled { background:#e9edf2; color:#8693a4; border-color:#e0e5ec; }
QLineEdit, QSpinBox, QPlainTextEdit { background:white; border:1px solid #d7dfe9; }
QComboBox { background:white; border:1px solid #d7dfe9; }
QMenu { background:white; border:1px solid #d7dfe9; }
QMenu::item:selected { background:#eaf0fa; }
QMenu::separator { background:#e6ecf4; }
QFrame#settingsPanel { background:white; border:1px solid #cbd8e8; }
QProgressBar { border:none; background:#e5eaf2; }
QProgressBar::chunk { background:#2463eb; }
QSplitter::handle { background:#dce4ee; }
QPushButton#settingsTab { color:#405570; }
QLabel#videoSurface { background:#edf2f8; color:#64748b; border-radius:8px; }
QLabel#videoSurface[playing="true"] { background:transparent; }
"""

DARK_QSS = """
QWidget { background:#131a24; color:#dbe4ef; font-size:13px; }
QLabel#muted { color:#93a3b8; font-size:12px; }
QPushButton { background:#243044; border:1px solid #33425a; }
QPushButton:hover { background:#2d3b52; }
QPushButton:checked { background:#1f2b3d; border-color:#3b4c67; }
QPushButton#primary { background:#2563eb; color:white; border:1px solid #2563eb; }
QPushButton:disabled { background:#1b2534; color:#6d7c90; border-color:#2a3547; }
QLineEdit, QSpinBox, QPlainTextEdit { background:#1b2534; border:1px solid #33425a; }
QComboBox { background:#1b2534; border:1px solid #33425a; }
QMenu { background:#1b2534; border:1px solid #2a3547; }
QMenu::item:selected { background:#2d3b52; }
QMenu::separator { background:#2a3547; }
QFrame#settingsPanel { background:#16202d; border:1px solid #2a3547; }
QProgressBar { border:none; background:#1b2534; }
QProgressBar::chunk { background:#2563eb; }
QSplitter::handle { background:#22303f; }
QPushButton#settingsTab { color:#a8b6c8; }
QLabel#videoSurface { background:#0f1720; color:#7a8ba0; border-radius:8px; }
QLabel#videoSurface[playing="true"] { background:transparent; }
"""


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


def stylesheet(mode):
    return (DARK_QSS if mode == DARK else LIGHT_QSS) + _STRUCTURE


# 画面区（VideoSurface）的两种状态配色。放在这里是为了跟整体主题一致，
# 同时避免每帧都去查 QSettings：apply() 时把模式缓存下来。
_SURFACE_COLORS = {
    LIGHT: ('#edf2f8', '#64748b'),
    DARK: ('#0f1720', '#7a8ba0'),
}
_cached_mode = None


def surface_style(playing):
    """画面区的内联样式（空白占位 / 正在播放）。"""
    global _cached_mode
    if _cached_mode is None:
        _cached_mode = current()
    background, foreground = _SURFACE_COLORS.get(_cached_mode, _SURFACE_COLORS[LIGHT])
    if playing:
        return 'background: transparent;'
    return f'background: {background}; color: {foreground}; border-radius: 8px;'


def apply(app, mode):
    """把整套界面样式贴到应用上；窗口不要再自己 setStyleSheet。"""
    global _cached_mode
    _cached_mode = mode
    if app is not None:
        app.setStyleSheet(stylesheet(mode))


def label(mode):
    return '浅色' if mode == DARK else '深色'
