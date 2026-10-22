import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import io
import sys
import tempfile
import threading
import unittest

from camera_monitor import crash_guard


class CrashGuardTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)   # addCleanup 后进先出：先关句柄再删目录
        self._original_excepthook = sys.excepthook
        self._original_thread_hook = threading.excepthook
        self._original_stderr = sys.stderr
        self.addCleanup(self._restore)

    def _restore(self):
        # 先松开日志句柄，否则 Windows 上临时目录删不掉
        crash_guard.uninstall()
        sys.excepthook = self._original_excepthook
        threading.excepthook = self._original_thread_hook
        sys.stderr = self._original_stderr

    def test_creates_the_crash_log_file(self):
        path = crash_guard.install(self.folder.name)
        self.assertEqual(path, os.path.join(self.folder.name, crash_guard.CRASH_FILE))
        self.assertTrue(os.path.exists(path))

    def test_uncaught_exception_is_logged(self):
        crash_guard.install(self.folder.name)
        sys.stderr = io.StringIO()
        with self.assertLogs('camera_monitor.crash_guard', level='CRITICAL') as logs:
            try:
                raise RuntimeError('boom')
            except RuntimeError:
                sys.excepthook(*sys.exc_info())
        self.assertIn('未捕获的异常', logs.output[0])
        self.assertIn('boom', logs.output[0])

    def test_thread_exception_is_logged(self):
        crash_guard.install(self.folder.name)
        args = threading.ExceptHookArgs((RuntimeError, RuntimeError('worker boom'), None, threading.current_thread()))
        with self.assertLogs('camera_monitor.crash_guard', level='CRITICAL') as logs:
            threading.excepthook(args)
        self.assertIn('worker boom', logs.output[0])

    def test_missing_folder_still_installs_hooks(self):
        # 日志目录不可用时也不能拦着程序启动：只装 Python 异常钩子
        self.assertIsNone(crash_guard.install(''))
        self.assertIs(sys.excepthook, crash_guard._excepthook)
        self.assertIs(threading.excepthook, crash_guard._thread_excepthook)
