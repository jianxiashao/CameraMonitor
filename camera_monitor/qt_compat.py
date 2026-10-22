"""Qt 6（PySide6）与 Qt 5（PySide2）的兼容层。

主版本仍然用 PySide6 / Qt 6。Windows 7 上跑不了 Qt 6，所以
`.github/workflows/windows-win7.yml` 用 Python 3.8 + PySide2 / Qt 5.15 构建：
本模块把 PySide2 以 PySide6 的名字注册进 `sys.modules`，源码里的
`from PySide6.QtCore import ...` 一行都不用改。

Qt 5 与 Qt 6 之间真正需要抹平的地方不多：
- Qt 6 把 QShortcut / QAction 从 QtWidgets 挪到了 QtGui；
- Qt 6 的 `exec()` 在 Qt 5 里叫 `exec_()`；
- `QTimer.singleShot()` 在 Qt 5 里没有带 context 的重载；
- 少数信号、返回值改了名或类型，见 socket_error_signal / drop_connection。

导入本模块是幂等的：反复导入只会检查一次。
"""
from __future__ import annotations

import importlib
import importlib.machinery
import sys

# 实际使用的绑定，方便日志和测试断言
QT_API = 'PySide6'

# Qt 6 与 Qt 5 的模块名前缀，两边一一对应
_ALIASED_PREFIXES = (('PySide6', 'PySide2'), ('shiboken6', 'shiboken2'))


class _AliasLoader:
    def __init__(self, module):
        self._module = module

    def create_module(self, spec):
        return self._module

    def exec_module(self, module):
        pass


class _Qt5AliasFinder:
    """把 `PySide6` / `PySide6.X` 的导入解析到 `PySide2` / `PySide2.X`。"""

    def find_spec(self, fullname, path=None, target=None):
        for prefix, replacement in _ALIASED_PREFIXES:
            if fullname == prefix or fullname.startswith(prefix + '.'):
                module = importlib.import_module(replacement + fullname[len(prefix):])
                # 直接登记到 sys.modules，下次导入不再走查找
                sys.modules[fullname] = module
                return importlib.machinery.ModuleSpec(fullname, _AliasLoader(module))
        return None


def _install_qt5_aliases():
    global QT_API
    if any(isinstance(finder, _Qt5AliasFinder) for finder in sys.meta_path):
        return
    try:
        importlib.import_module('PySide6')
    except ImportError:
        pass
    else:
        return
    try:
        importlib.import_module('PySide2')
    except ImportError:
        # 两套绑定都不在：不要把 ImportError 吞掉，让原来的报错照常出现
        return
    sys.meta_path.insert(0, _Qt5AliasFinder())
    QT_API = 'PySide2'

    QtGui = importlib.import_module('PySide2.QtGui')
    QtWidgets = importlib.import_module('PySide2.QtWidgets')
    for name in ('QShortcut', 'QAction'):  # Qt 6 才挪到 QtGui
        if not hasattr(QtGui, name):
            setattr(QtGui, name, getattr(QtWidgets, name))
    for name in ('QApplication', 'QDialog', 'QMenu'):  # Qt 5 只提供 exec_()
        cls = getattr(QtWidgets, name)
        if not hasattr(cls, 'exec'):
            setattr(cls, 'exec', cls.exec_)

    # Qt 5 的信号叫 error，Qt 6 改名为 errorOccurred；补个别名，
    # 直接写 errorOccurred 的代码（含测试）两边都能跑
    QWebSocket = importlib.import_module('PySide2.QtWebSockets').QWebSocket
    if not hasattr(QWebSocket, 'errorOccurred'):
        setattr(QWebSocket, 'errorOccurred', QWebSocket.error)

    _install_single_shot_context()
    _install_event_position_aliases()
    _install_qt_test_helpers()


def _install_single_shot_context():
    """让 `QTimer.singleShot(msec, context, callback)` 在 Qt 5 上也能用。

    Qt 6 支持带 context 的重载（context 先销毁就不回调），PySide2 只暴露
    `singleShot(int, callable)`。用一个挂在 context 下的单次 QTimer 达到同样效果。
    """
    from PySide6.QtCore import QObject, QTimer

    native = QTimer.singleShot
    if getattr(native, '_camera_monitor_context_aware', False):
        return

    def single_shot(msec, *args):
        if len(args) == 2 and isinstance(args[0], QObject):
            context, callback = args
            timer = QTimer(context)
            timer.setSingleShot(True)
            timer.timeout.connect(callback)
            timer.timeout.connect(timer.deleteLater)
            timer.start(msec)
            return None
        return native(msec, *args)

    single_shot._camera_monitor_context_aware = True
    QTimer.singleShot = staticmethod(single_shot)


def _install_event_position_aliases():
    """Qt 6 把鼠标事件的 `localPos()` / `globalPos()` 改名为 `position()` / `globalPosition()`。"""
    from PySide6.QtGui import QMouseEvent

    for new_name, old_name in (('position', 'localPos'), ('globalPosition', 'globalPos')):
        if not hasattr(QMouseEvent, new_name):
            setattr(QMouseEvent, new_name, getattr(QMouseEvent, old_name))


def _install_qt_test_helpers():
    """补上只在测试里用得到、PySide2 又没有暴露的 QtTest 接口。

    打包后的程序不含 QtTest，这里导入失败就直接跳过。
    """
    try:
        QtTest = importlib.import_module('PySide2.QtTest')
    except ImportError:
        return
    QTest = QtTest.QTest
    if hasattr(QTest, 'qWait'):
        return
    import time

    from PySide6.QtCore import QCoreApplication, QEventLoop

    def qWait(msec):
        """等价 QTest::qWait：反复处理事件，直到 msec 毫秒过去。"""
        deadline = time.monotonic() + msec / 1000.0
        while True:
            QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 10)
            if time.monotonic() >= deadline:
                return
            time.sleep(0.001)

    QTest.qWait = staticmethod(qWait)


def socket_error_signal(socket):
    """Qt 6 的 `errorOccurred` 在 Qt 5 里叫 `error`。"""
    return getattr(socket, 'errorOccurred', None) or socket.error


def drop_connection(owner, connection):
    """断开 `connect()` 的返回值。

    Qt 6 返回 QMetaObject.Connection，PySide6 能用它精确断开；
    Qt 5 返回 bool，连接随信号发射者销毁自动断开，这里什么也不用做。
    """
    if connection is None or isinstance(connection, bool):
        return
    owner.disconnect(connection)


_install_qt5_aliases()
