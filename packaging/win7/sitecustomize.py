"""Windows 7 构建环境（Python 3.8 + PySide2）里的测试引导文件。

tests/ 目录下的模块是在顶层 `from PySide6.QtCore import ...` 的，而 Win7 版本
只能用 PySide2，所以必须在解释器启动阶段就把 PySide6 的名字映射过去。
把它们放进 PYTHONPATH 后，Python 启动时会自动执行本文件：

    set CAMERA_MONITOR_ROOT=%CD%
    set PYTHONPATH=%CD%\packaging\win7
    python -m unittest discover -s tests -v

没有 PySide2 的环境（PySide6 或两套绑定都没有）里，这里什么也不会做。
"""
import os
import sys

_ROOT = os.environ.get('CAMERA_MONITOR_ROOT') or os.getcwd()
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    import camera_monitor.qt_compat as qt_compat
except ImportError:
    qt_compat = None

if qt_compat is not None and qt_compat.QT_API == 'PySide2':
    # Qt 5 里关掉最后一个窗口会给线程置 quitNow，此后所有 QEventLoop::exec() 都直接
    # 返回：测试之间只要有一个用例关了窗口，后面 request_unlock / exec() 之类的
    # 模态循环就全都不再处理事件（Qt 6 已经去掉了这个机制）。这里统一关掉它。
    # 产品本身只有一个事件循环，关闭窗口就是要退出，不受影响。
    from PySide2.QtWidgets import QApplication

    QApplication.setQuitOnLastWindowClosed(False)
