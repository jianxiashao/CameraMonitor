import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from support import make_window


class ClosingFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_a_slow_shutdown_tells_the_user_it_is_stopping(self):
        window = make_window(self)
        window.show()
        # 线程收尾慢时窗口会先拒绝关闭、200 毫秒后再试，期间必须让人看见"在停"
        with patch.object(window.thumbnails, 'busy', return_value=True):
            accepted = window.close()
        self.assertFalse(accepted, '收尾没完成时窗口不能被关掉')
        self.assertIn('正在停止', window.status.text())

    def test_the_notice_is_only_written_once(self):
        window = make_window(self)
        window.show_stopping()
        window.status.setText('别的内容')
        window.show_stopping()
        self.assertEqual('别的内容', window.status.text(), '提示只该写一次，不能反复覆盖状态栏')


if __name__ == '__main__':
    unittest.main()
