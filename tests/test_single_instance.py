import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest

from camera_monitor.single_instance import acquire


class SingleInstanceTests(unittest.TestCase):
    def test_second_instance_is_refused_until_the_first_lets_go(self):
        with tempfile.TemporaryDirectory() as folder:
            first = acquire(folder)
            self.assertIsNotNone(first, '第一个实例应当拿到锁')
            try:
                self.assertIsNone(acquire(folder), '第二个实例必须被拒绝')
            finally:
                first.unlock()

            second = acquire(folder)
            self.assertIsNotNone(second, '前一个实例退出后应当能重新启动')
            second.unlock()

    def test_unwritable_folder_does_not_block_startup(self):
        # 目录建不出来时不能反过来让程序起不来：不加锁，但照常返回
        with tempfile.NamedTemporaryFile() as handle:
            lock = acquire(handle.name)
        self.assertIsNotNone(lock)
        lock.unlock()
