"""同一时间只跑一个实例。

双击两次会起两套解码线程抢同一批相机：多数相机限制并发连接，后来的那一路会把
先前的一路挤掉；两个进程还会同时写设置与本机快照，云端下行也会互相顶。
这里用 QLockFile 占住 AppData 下的锁文件，第二个实例拿不到锁就直接退出。
"""
import os

from PySide6.QtCore import QLockFile, QStandardPaths
from PySide6.QtNetwork import QLocalServer, QLocalSocket

LOCK_NAME = 'instance.lock'
# 进程被强杀时锁文件会留下来；超过这个时间没被刷新，才当成残留锁
STALE_MS = 30_000
# 自动重启时新进程比旧进程先起来：等旧进程放开锁，别把它当成「已有实例」退出
RESTART_FLAG = '--restarting'


class _NoLock:
    """拿不到可用目录时的占位：不加锁，但也不拦着程序启动。"""

    def unlock(self):
        pass


def default_folder():
    folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return folder or os.path.join(os.path.expanduser('~'), '.camera-monitor')


def acquire(folder=None, wait_ms=100):
    """拿到锁返回 QLockFile（调用方要一直持有它），已有实例在跑则返回 None。

    目录建不出来时不加锁（返回占位对象）：单实例是锦上添花，不能反过来让程序起不来。
    wait_ms 用于自动重启：新进程多等一会儿，让旧进程先把锁放掉。
    """
    directory = folder or default_folder()
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError:
        return _NoLock()
    lock = QLockFile(os.path.join(directory, LOCK_NAME))
    lock.setStaleLockTime(STALE_MS)
    remaining = max(0, int(wait_ms))
    while True:
        if lock.tryLock(min(100, remaining) if remaining else 0):
            return lock
        if remaining <= 0:
            return None
        remaining -= 100


SERVER_NAME = 'CameraMonitor-activate-v1'


def start_activation_server(on_activate):
    """第一个实例监听；第二个实例双击时把已有窗口唤到前台。"""
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        return None

    def accept():
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            socket.readyRead.connect(socket.deleteLater)
            try:
                on_activate()
            except Exception:
                pass
            socket.disconnectFromHost()

    server.newConnection.connect(accept)
    return server


def signal_existing():
    """第二个实例启动时调用；成功说明第一个实例还在。"""
    for _ in range(5):
        socket = QLocalSocket()
        socket.connectToServer(SERVER_NAME)
        if socket.waitForConnected(200):
            socket.write(b'activate')
            socket.waitForBytesWritten(200)
            socket.disconnectFromServer()
            return True
        socket.abort()
    return False
