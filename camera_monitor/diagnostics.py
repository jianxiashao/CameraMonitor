"""把现场排障需要的东西打包成一个 zip：系统信息、脱敏设置、运行日志、各路诊断。

现场电脑出问题时，维护人员不用再教用户去 AppData 里翻日志：
点一下"导出诊断包"，把 zip 发过来即可。凭据、令牌、密码一律不写进去。
"""
import json
import os
import platform
import sys
import zipfile
from datetime import datetime

from PySide6 import QtCore

from . import __version__

# 键名里出现这些词的设置一律不进诊断包
SENSITIVE_HINTS = ('password', 'secret', 'token', 'auth', 'cookie', 'credential', 'passwd')

SYSTEM_FILE = 'system.txt'
SETTINGS_FILE = 'settings.json'
PLAYERS_FILE = 'players.txt'
LOGS_FOLDER = 'logs'
MAX_LOG_FILES = 4


def system_summary():
    lines = [
        f'Camera Monitor {__version__}',
        f'导出时间: {datetime.now():%Y-%m-%d %H:%M:%S}',
        f'系统: {platform.platform()}',
        f'Python: {sys.version.split()[0]}',
        f'Qt: {QtCore.qVersion()}',
        f'主机名: {platform.node()}',
    ]
    try:
        import psutil
        memory = psutil.virtual_memory()
        lines.append(f'CPU: {psutil.cpu_count()} 核，当前占用 {psutil.cpu_percent(interval=0.2)}%')
        lines.append(f'内存: 共 {memory.total // (1024 ** 2)} MB，可用 {memory.available // (1024 ** 2)} MB')
    except Exception:
        # 拿不到系统指标不影响导出，宁可少几行
        pass
    return '\n'.join(lines)


def is_sensitive(key):
    lowered = str(key).lower()
    return any(hint in lowered for hint in SENSITIVE_HINTS)


def redacted_settings(settings):
    """导出设置，但把密码/令牌类键名整条跳过。"""
    data = {}
    for key in sorted(settings.allKeys()):
        if is_sensitive(key):
            continue
        value = settings.value(key)
        data[key] = value if isinstance(value, (int, float, bool)) else str(value)
    return data


def player_report(players):
    blocks = []
    for player in players:
        blocks.append(f'=== {player.device.ip} ===')
        try:
            detail = player.connection_diagnostics.toPlainText()
        except AttributeError:
            detail = ''
        blocks.append(detail or '（这一路还没有诊断日志）')
        blocks.append('')
    return '\n'.join(blocks)


def collect(destination, log_dir='', settings=None, players=()):
    """写一个诊断 zip，返回实际路径（自动补 .zip 后缀）。

    任何一步失败都抛出去，由调用方提示用户；这里不吞异常，
    否则用户拿到的是一个缺内容的压缩包却以为导成功了。
    """
    destination = str(destination)
    if not destination.lower().endswith('.zip'):
        destination += '.zip'
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(SYSTEM_FILE, system_summary())
        if settings is not None:
            archive.writestr(SETTINGS_FILE, json.dumps(redacted_settings(settings), ensure_ascii=False, indent=2))
        players = list(players)
        if players:
            archive.writestr(PLAYERS_FILE, player_report(players))
        if log_dir and os.path.isdir(log_dir):
            names = [name for name in sorted(os.listdir(log_dir)) if name.endswith(('.log', '.txt'))]
            for name in names[-MAX_LOG_FILES:]:
                path = os.path.join(log_dir, name)
                if os.path.isfile(path):
                    archive.write(path, os.path.join(LOGS_FOLDER, name))
    return destination
