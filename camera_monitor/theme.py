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
QPushButton { border-radius:6px; padding:7px 10px; }
QPushButton#primary { font-weight:600; }
QLineEdit, QSpinBox, QPlainTextEdit { border-radius:5px; padding:5px; }
QComboBox { border-radius:5px; padding:5px 8px; }
QMenu { border-radius:6px; padding:4px; }
QMenu::item { padding:6px 24px 6px 16px; border-radius:4px; }
QMenu::separator { height:1px; margin:4px 8px; }
QScrollArea { border:none; }
QFrame#settingsPanel { border-radius:8px; }
QSplitter::handle { width:8px; background:transparent; }
"""

LIGHT_QSS = """
QWidget { background:#ffffff; color:#0f172a; font-size:13px; }
QWidget#appRoot { background:#eef3f9; }
QFrame#appHeader { background:transparent; }
QLabel#appTitle { font-size:21px; font-weight:700; color:#0f172a; }
QLabel#appSubtitle { font-size:12px; color:#64748b; }
QLabel#appLogo, QLabel#appTitle, QLabel#appSubtitle { background:transparent; }
QLabel#topBadge { background:#e8f0ff; color:#2563eb; border:1px solid #d6e6ff; border-radius:10px; padding:4px 12px; font-size:12px; font-weight:600; }
QWidget#sidebarCard { background:#ffffff; border:1px solid #e2e8f0; border-radius:16px; }
QWidget#sidebarCard QLabel { background:transparent; }
QLabel#sectionTitle { font-size:16px; font-weight:700; color:#0f172a; }
QLabel#countBadge { background:#eef4ff; color:#2563eb; border-radius:9px; padding:1px 8px; font-size:11px; font-weight:600; }
QLineEdit#searchField { background:#f8fafc; border:1px solid #e2e8f0; border-radius:9px; padding:8px 12px; }
QLineEdit#searchField:focus { border-color:#93b4f8; background:#ffffff; }
QPushButton#ghost { background:transparent; border:1px solid transparent; color:#475569; padding:7px 10px; }
QPushButton#ghost:hover { background:#f1f5f9; border-color:#e2e8f0; }
QPushButton#accentSoft { background:#eff6ff; border:1px solid #bfdbfe; color:#1d4ed8; font-weight:600; }
QPushButton#accentSoft:hover { background:#e0efff; }
QPushButton#seg { background:#f8fafc; border:1px solid #e2e8f0; color:#334155; padding:6px 11px; }
QPushButton#seg:hover { background:#eef4ff; border-color:#bfdbfe; }
QPushButton#deviceRow { background:#ffffff; border:1px solid #e8eef6; border-radius:12px; padding:0; }
QPushButton#deviceRow:hover { background:#f8fbff; border-color:#cfe0f6; }
QPushButton#deviceRow:checked { background:#eef6ff; border:1px solid #a9c8f5; border-left:3px solid #2563eb; }
QPushButton#deviceRow QLabel { background:transparent; }
QPushButton#deviceThumbnail { background:#eef3f9; border-radius:8px; }
QLabel#deviceStatus { font-size:11px; font-weight:600; }
QWidget#wallPanel { background:transparent; }
QScrollArea#wallScroll, QScrollArea#wallScroll > QWidget > QWidget { background:transparent; border:none; }
QWidget#toolbarCard { background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; }
QWidget#layoutCard { background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; }
QWidget#toolbarCard QLabel, QWidget#layoutCard QLabel { background:transparent; }
QLabel#wallTitle { font-size:19px; font-weight:700; color:#0f172a; }
QLabel#subsectionTitle { font-size:12px; font-weight:600; color:#64748b; }
QWidget#watchCanvas { background:#0b1422; border-radius:14px; }
QWidget#watchCanvas[presentation="true"] { background:#0b1422; border-radius:0px; }
QLabel#wallHint { color:#94a3b8; font-size:12px; padding:6px; }
QFrame#sidebarDivider { background:#eef2f7; }
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
QFrame#settingsPanel { background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; }
QLabel#panelTitle { font-size:15px; font-weight:700; }
QProgressBar { border:none; background:#e5eaf2; }
QProgressBar::chunk { background:#2463eb; }
QSplitter::handle { background:transparent; }
QLabel#videoSurface { background:#0f1a2b; color:#7d8da3; border-radius:8px; }
QLabel#videoSurface[playing="true"] { background:transparent; }
QPushButton#deviceRow { background:transparent; border:none; border-bottom:1px solid #e9eef5; border-radius:0; padding:8px; }
QPushButton#deviceRow:hover { background:#f2f6fc; }
QPushButton#deviceRow:checked { background:#e5efff; border-left:3px solid #2463eb; }
QPushButton#deviceRow QLabel { background:transparent; border:none; }
QPushButton#deviceThumbnail { padding:0; border:0; border-radius:4px; background:#edf2f8; color:#64748b; font-size:11px; }
QWidget#deviceListHeader { background:#eaf0f7; border-radius:6px; font-weight:600; }
QFrame#sidebarDivider { background:#dce4ee; max-height:1px; }
QWidget#welcomePage { background:#f2f5fb; }
QFrame#welcomeCard { background:white; border-radius:16px; }
QFrame#welcomeCard QLabel { background:transparent; }
QLabel#welcomeTitle { font-size:26px; font-weight:700; color:#111827; }
QLabel#welcomeHint { color:#6b7280; font-size:14px; }
QLabel#welcomeError { color:#c0392b; font-size:13px; }
QLineEdit#welcomeCode { font-size:24px; padding:12px; border:2px solid #2463eb; border-radius:10px; background:white; }
QPushButton#welcomeStart { background:#2463eb; color:white; font-size:18px; font-weight:600; padding:12px; border-radius:10px; border:none; }
QPushButton#welcomeStart:disabled { background:#9db7f5; }
QPushButton#welcomeAlone { background:transparent; border:none; color:#2463eb; font-size:13px; }
QScrollBar:vertical { width:9px; background:transparent; margin:2px; }
QScrollBar::handle:vertical { background:#cbd5e1; border-radius:4px; min-height:24px; }
QScrollBar::handle:vertical:hover { background:#94a3b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid #cbd5e1; border-radius:4px; background:#ffffff; }
QCheckBox::indicator:checked { background:#2563eb; border-color:#2563eb; }
QToolTip { background:#0f172a; color:#f8fafc; border:none; padding:6px 8px; border-radius:6px; }
QDialog#aboutDialog { background:#eef3f9; }
QFrame#aboutCard { background:#ffffff; border:1px solid #e2e8f0; border-radius:18px; }
QLabel#aboutTitle { font-size:23px; font-weight:700; color:#0f172a; }
QLabel#aboutSubtitle { font-size:13px; color:#64748b; }
QLabel#aboutVersion { font-size:12px; color:#2563eb; font-weight:600; }
QLabel#aboutText { font-size:13px; color:#334155; }
QLabel#aboutMeta { font-size:12px; color:#64748b; }
QPushButton#aboutLink { background:#f8fafc; border:1px solid #e2e8f0; color:#2563eb; padding:6px 10px; }
QPushButton#aboutLink:hover { background:#eef4ff; border-color:#bfdbfe; }
"""

DARK_QSS = """
QWidget { background:#162235; color:#e2e8f0; font-size:13px; }
QWidget#appRoot { background:#0b1220; }
QFrame#appHeader { background:transparent; }
QLabel#appTitle { font-size:21px; font-weight:700; color:#e2e8f0; }
QLabel#appSubtitle { font-size:12px; color:#93a3b8; }
QLabel#appLogo, QLabel#appTitle, QLabel#appSubtitle { background:transparent; }
QLabel#topBadge { background:#172a4a; color:#93c5fd; border:1px solid #2f4f7a; border-radius:10px; padding:4px 12px; font-size:12px; font-weight:600; }
QWidget#sidebarCard { background:#162235; border:1px solid #263549; border-radius:16px; }
QWidget#sidebarCard QLabel { background:transparent; }
QLabel#sectionTitle { font-size:16px; font-weight:700; color:#e2e8f0; }
QLabel#countBadge { background:#172a4a; color:#93c5fd; border-radius:9px; padding:1px 8px; font-size:11px; font-weight:600; }
QLineEdit#searchField { background:#101a2b; border:1px solid #2a3a50; border-radius:9px; padding:8px 12px; }
QLineEdit#searchField:focus { border-color:#3b82f6; background:#101a2b; }
QPushButton#ghost { background:transparent; border:1px solid transparent; color:#cbd5e1; padding:7px 10px; }
QPushButton#ghost:hover { background:#1f2e44; border-color:#2a3a50; }
QPushButton#accentSoft { background:#172a4a; border:1px solid #2f4f7a; color:#93c5fd; font-weight:600; }
QPushButton#accentSoft:hover { background:#1d3355; }
QPushButton#seg { background:#101a2b; border:1px solid #2a3a50; color:#cbd5e1; padding:6px 11px; }
QPushButton#seg:hover { background:#1f2e44; border-color:#3b82f6; }
QPushButton#deviceRow { background:#162235; border:1px solid #22324a; border-radius:12px; padding:0; }
QPushButton#deviceRow:hover { background:#1b2a40; border-color:#2f4560; }
QPushButton#deviceRow:checked { background:#172a4a; border:1px solid #2f5f9f; border-left:3px solid #3b82f6; }
QPushButton#deviceRow QLabel { background:transparent; }
QPushButton#deviceThumbnail { background:#101a2b; border-radius:8px; }
QLabel#deviceStatus { font-size:11px; font-weight:600; }
QWidget#wallPanel { background:transparent; }
QScrollArea#wallScroll, QScrollArea#wallScroll > QWidget > QWidget { background:transparent; border:none; }
QWidget#toolbarCard { background:#162235; border:1px solid #263549; border-radius:14px; }
QWidget#layoutCard { background:#162235; border:1px solid #263549; border-radius:14px; }
QWidget#toolbarCard QLabel, QWidget#layoutCard QLabel { background:transparent; }
QLabel#wallTitle { font-size:19px; font-weight:700; color:#e2e8f0; }
QLabel#subsectionTitle { font-size:12px; font-weight:600; color:#93a3b8; }
QWidget#watchCanvas { background:#060d17; border-radius:14px; }
QWidget#watchCanvas[presentation="true"] { background:#060d17; border-radius:0px; }
QLabel#wallHint { color:#7d8da3; font-size:12px; padding:6px; }
QFrame#sidebarDivider { background:#22303f; }
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
QFrame#settingsPanel { background:#162235; border:1px solid #263549; border-radius:14px; }
QLabel#panelTitle { font-size:15px; font-weight:700; }
QProgressBar { border:none; background:#1b2534; }
QProgressBar::chunk { background:#2563eb; }
QSplitter::handle { background:transparent; }
QLabel#videoSurface { background:#0f1720; color:#7a8ba0; border-radius:8px; }
QLabel#videoSurface[playing="true"] { background:transparent; }
QPushButton#deviceRow { background:transparent; border:none; border-bottom:1px solid #22303f; border-radius:0; padding:8px; }
QPushButton#deviceRow:hover { background:#1a2432; }
QPushButton#deviceRow:checked { background:#1d2a3d; border-left:3px solid #3b82f6; }
QPushButton#deviceRow QLabel { background:transparent; border:none; }
QPushButton#deviceThumbnail { padding:0; border:0; border-radius:4px; background:#1b2534; color:#93a3b8; font-size:11px; }
QWidget#deviceListHeader { background:#1a2432; border-radius:6px; font-weight:600; }
QFrame#sidebarDivider { background:#22303f; max-height:1px; }
QWidget#welcomePage { background:#0f1621; }
QFrame#welcomeCard { background:#1b2534; border-radius:16px; }
QFrame#welcomeCard QLabel { background:transparent; }
QLabel#welcomeTitle { font-size:26px; font-weight:700; color:#e5edf7; }
QLabel#welcomeHint { color:#93a3b8; font-size:14px; }
QLabel#welcomeError { color:#f87171; font-size:13px; }
QLineEdit#welcomeCode { font-size:24px; padding:12px; border:2px solid #3b82f6; border-radius:10px; background:#101a28; color:#e5edf7; }
QPushButton#welcomeStart { background:#2563eb; color:white; font-size:18px; font-weight:600; padding:12px; border-radius:10px; border:none; }
QPushButton#welcomeStart:disabled { background:#33425a; }
QPushButton#welcomeAlone { background:transparent; border:none; color:#7aa2ff; font-size:13px; }
QScrollBar:vertical { width:9px; background:transparent; margin:2px; }
QScrollBar::handle:vertical { background:#334155; border-radius:4px; min-height:24px; }
QScrollBar::handle:vertical:hover { background:#475569; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid #334155; border-radius:4px; background:#101a2b; }
QCheckBox::indicator:checked { background:#2563eb; border-color:#2563eb; }
QToolTip { background:#0b1220; color:#e2e8f0; border:1px solid #263549; padding:6px 8px; border-radius:6px; }
QDialog#aboutDialog { background:#0b1220; }
QFrame#aboutCard { background:#162235; border:1px solid #263549; border-radius:18px; }
QLabel#aboutTitle { font-size:23px; font-weight:700; color:#e2e8f0; }
QLabel#aboutSubtitle { font-size:13px; color:#93a3b8; }
QLabel#aboutVersion { font-size:12px; color:#93c5fd; font-weight:600; }
QLabel#aboutText { font-size:13px; color:#cbd5e1; }
QLabel#aboutMeta { font-size:12px; color:#93a3b8; }
QPushButton#aboutLink { background:#101a2b; border:1px solid #2a3a50; color:#93c5fd; padding:6px 10px; }
QPushButton#aboutLink:hover { background:#1f2e44; border-color:#3b82f6; }
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
    LIGHT: ('#0f1a2b', '#7d8da3'),
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
