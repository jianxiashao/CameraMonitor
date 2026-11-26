import csv
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from camera_monitor.event_log import AlertLog


class AlertLogTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.log = AlertLog(os.path.join(self.folder.name, 'events.db'))
        self.addCleanup(self.log.close)

    def test_records_are_listed_newest_first(self):
        self.log.record('10.0.0.1', '画面异常', '画面可能全黑')
        self.log.record('10.0.0.2', '画面恢复', '恢复正常')
        rows = self.log.recent()
        self.assertEqual(2, len(rows))
        self.assertEqual('10.0.0.2', rows[0]['ip'])
        self.assertEqual('画面异常', rows[1]['kind'])

    def test_export_and_clear(self):
        self.log.record('10.0.0.1', '画面异常', '黑屏')
        target = Path(self.folder.name) / 'out.csv'
        self.log.export_csv(str(target))
        with open(target, encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(['时间', 'IP', '类型', '内容'], rows[0])
        self.assertEqual('10.0.0.1', rows[1][1])
        self.log.clear()
        self.assertEqual([], self.log.recent())

    def test_old_records_are_pruned(self):
        old = datetime.now() - timedelta(days=91)
        self.log.record('10.0.0.1', '画面异常', '旧记录', at=old)
        self.log.record('10.0.0.2', '画面异常', '新记录')
        self.assertEqual(['10.0.0.2'], [row['ip'] for row in self.log.recent()])


if __name__ == '__main__':
    unittest.main()
