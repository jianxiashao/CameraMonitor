"""告警记录查看/导出。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from .event_log import AlertLog


class EventLogDialog(QDialog):
    def __init__(self, log: AlertLog, parent=None):
        super().__init__(parent)
        self.log = log
        self.setWindowTitle('告警记录')
        self.resize(860, 520)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(['时间', '摄像头 IP', '类型', '内容'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        refresh = QPushButton('刷新')
        refresh.clicked.connect(self.reload)
        export = QPushButton('导出 CSV…')
        export.clicked.connect(self.export)
        clear = QPushButton('清空')
        clear.clicked.connect(self.clear)
        close = QPushButton('关闭')
        close.clicked.connect(self.close)
        buttons.addWidget(refresh)
        buttons.addWidget(export)
        buttons.addWidget(clear)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self.reload()

    def reload(self):
        rows = self.log.recent()
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, value in enumerate((row['at'], row['ip'], row['kind'], row['message'])):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(index, column, item)
        self.table.resizeColumnsToContents()

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, '导出告警记录', '告警记录.csv', 'CSV (*.csv)')
        if not path:
            return
        if not path.lower().endswith('.csv'):
            path += '.csv'
        try:
            self.log.export_csv(path)
        except OSError:
            QMessageBox.warning(self, '导出告警记录', '写入失败，请换一个目录再试。')
            return
        QMessageBox.information(self, '导出告警记录', f'已导出到：\n{path}')

    def clear(self):
        answer = QMessageBox.question(self, '清空告警记录', '确定要删除全部告警记录吗？')
        if answer == QMessageBox.StandardButton.Yes:
            self.log.clear()
            self.reload()


__all__ = ['EventLogDialog']
