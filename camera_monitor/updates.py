"""检查 GitHub Release 上有没有新版本。只在用户点菜单时联网。"""
from __future__ import annotations

import requests
from PySide6.QtCore import QThread, Signal

API_URL = 'https://api.github.com/repos/jianxiashao/CameraMonitor/releases/latest'
TIMEOUT = (3.0, 5.0)


def version_tuple(value):
    parts = []
    for piece in str(value).lstrip('vV').split('.'):
        digits = ''.join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


class UpdateWorker(QThread):
    result = Signal(str, str, str)   # latest_tag, html_url, error

    def run(self):
        try:
            response = requests.get(API_URL, timeout=TIMEOUT, allow_redirects=False,
                                    headers={'Accept': 'application/vnd.github+json'})
            if response.status_code != 200:
                self.result.emit('', '', f'HTTP {response.status_code}')
                return
            payload = response.json()
            self.result.emit(str(payload.get('tag_name') or ''), str(payload.get('html_url') or ''), '')
        except Exception as exc:
            # 不把底层异常文本带到界面
            self.result.emit('', '', type(exc).__name__)
