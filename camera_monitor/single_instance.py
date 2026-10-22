"""同一时间只跑一个实例。

双击两次会起两套解码线程抢同一批相机：多数相机限制并发连接，后来的那一路会把
先前的一路挤掉；两个进程还会同时写设置与本机快照，云端下行也会互相顶。
这里用 QLockFile 占住 AppData 下的锁文件，第二个实例拿不到锁就直接退出。
"""
import os

from PySide6.QtCore import QLockFile, QStandardPaths

LOCK_NAME = 'instance.lock'
# 进程被强杀时锁文件会留下来；超过这个时间没被刷新，才当成残留锁
STALE_MS = 30_000


class _NoLock:
    """拿不到可用目录时的占位：不加锁，但也不拦着程序启动。"""

    def unlock(self):
        pass


def default_folder():
    folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return folder or os.path.join(os.path.expanduser('~'), '.camera-monitor')


def acquire(folder=None):
    """拿到锁返回 QLockFile（调用方要一直持有它），已有实例在跑则返回 None。

    目录建不出来时不加锁（返回占位对象）：单实例是锦上添花，不能反过来让程序起不来。
    """
    directory = folder or default_folder()
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError:
        return _NoLock()
    lock = QLockFile(os.path.join(directory, LOCK_NAME))
    lock.setStaleLockTime(STALE_MS)
    return lock if lock.tryLock(100) else None
