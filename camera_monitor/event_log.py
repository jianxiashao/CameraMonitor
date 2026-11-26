"""画面异常/恢复的历史记录，落 SQLite，便于事后查证和导出。"""
from __future__ import annotations

import csv
import os
import sqlite3
import sys
import threading
from datetime import datetime, timedelta

from PySide6.QtCore import QStandardPaths

DB_NAME = 'events.db'


def default_path():
    """测试里用内存库，绝不写开发机的真实数据。"""
    if 'unittest' in ' '.join(sys.argv) or os.environ.get('CAMERA_MONITOR_NO_ALERTS'):
        return ':memory:'
    folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return os.path.join(folder, DB_NAME) if folder else ':memory:'


class AlertLog:
    def __init__(self, path=None):
        self.path = path or default_path()
        if self.path != ':memory:':
            folder = os.path.dirname(self.path)
            try:
                if folder:
                    os.makedirs(folder, exist_ok=True)
            except OSError:
                self.path = ':memory:'
        self._lock = threading.Lock()
        try:
            self._connection = sqlite3.connect(self.path, check_same_thread=False)
            with self._lock:
                self._connection.execute(
                    'CREATE TABLE IF NOT EXISTS events ('
                    'id INTEGER PRIMARY KEY AUTOINCREMENT,'
                    'at TEXT NOT NULL, ip TEXT NOT NULL, kind TEXT NOT NULL, message TEXT)')
                self._connection.execute('CREATE INDEX IF NOT EXISTS events_at ON events(at)')
                self._connection.commit()
        except sqlite3.Error:
            # 磁盘满/权限不足时告警历史不是关键路径，降级成内存库，别让监控起不来
            self.path = ':memory:'
            self._connection = sqlite3.connect(':memory:', check_same_thread=False)
            with self._lock:
                self._connection.execute(
                    'CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT,'
                    'at TEXT NOT NULL, ip TEXT NOT NULL, kind TEXT NOT NULL, message TEXT)')
                self._connection.execute('CREATE INDEX events_at ON events(at)')
                self._connection.commit()

    def record(self, ip, kind, message='', at=None):
        stamp = (at or datetime.now()).isoformat(timespec='seconds')
        with self._lock:
            self._connection.execute(
                'INSERT INTO events(at, ip, kind, message) VALUES (?,?,?,?)',
                (stamp, str(ip), str(kind), str(message or '')))
            self._connection.commit()
        self.prune()

    def recent(self, limit=500):
        with self._lock:
            rows = self._connection.execute(
                'SELECT at, ip, kind, message FROM events ORDER BY id DESC LIMIT ?',
                (max(1, int(limit)),)).fetchall()
        return [{'at': row[0], 'ip': row[1], 'kind': row[2], 'message': row[3]} for row in rows]

    def prune(self, days=90):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec='seconds')
        with self._lock:
            self._connection.execute('DELETE FROM events WHERE at < ?', (cutoff,))
            self._connection.commit()

    def clear(self):
        with self._lock:
            self._connection.execute('DELETE FROM events')
            self._connection.commit()

    def export_csv(self, path):
        rows = self.recent(limit=100000)
        with open(path, 'w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['时间', 'IP', '类型', '内容'])
            for row in rows:
                writer.writerow([row['at'], row['ip'], row['kind'], row['message']])
        return path

    def close(self):
        with self._lock:
            try:
                self._connection.close()
            except sqlite3.Error:
                pass
