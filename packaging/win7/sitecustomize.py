"""Windows 7 构建环境（Python 3.8 + PySide2）里的测试引导文件。

它做两件事，都是源码环境（跑测试）才需要、打包后的 exe 由 spec 负责的：

1. tests/ 目录下的模块是在顶层 `from PySide6.QtCore import ...` 的，而 Win7 版本
   只能用 PySide2，所以必须在解释器启动阶段就把 PySide6 的名字映射过去。

2. Qt 5.15 的 QtNetwork 编译时并不链接 OpenSSL，运行时才按名字去找
   libssl-1_1-x64.dll / libcrypto-1_1-x64.dll。找不到时 QSslSocket.supportsSsl()
   返回 False，云端下行通道（wss）永远连不上——而且没有任何报错。
   这里把 CPython 3.8 自带的 OpenSSL 1.1 复制成 Qt 期望的名字，并把目录放进 PATH。

把它们放进 PYTHONPATH 后，Python 启动时会自动执行本文件：

    set CAMERA_MONITOR_ROOT=%CD%
    set PYTHONPATH=%CD%\packaging\win7
    python -m unittest discover -s tests -v

没有 PySide2 的环境（PySide6 或两套绑定都没有）里，这里什么也不会做。
"""
import os
import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

_ROOT = os.environ.get('CAMERA_MONITOR_ROOT') or os.getcwd()
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    import camera_monitor.qt_compat as qt_compat
except ImportError:
    qt_compat = None


def _prepare_openssl():
    """让 QtNetwork 在源码环境里也能用上 TLS，返回复制出的目录。"""
    if sys.platform != 'win32':
        return None
    folder = _HERE / 'openssl'
    python_dir = Path(sys.base_prefix)
    for name in ('libssl-1_1', 'libcrypto-1_1'):
        target = folder / (name + '-x64.dll')
        if target.exists():
            continue
        found = (sorted((python_dir / 'DLLs').glob(name + '*.dll'))
                 or sorted(python_dir.glob(name + '*.dll')))
        if not found:
            # 找不到就不拦着：只是在源码环境下 wss 用不了，测试会如实报出来
            continue
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(found[0]), str(target))
    return folder if folder.is_dir() else None


if qt_compat is not None and qt_compat.QT_API == 'PySide2':
    # Qt 5 里关掉最后一个窗口会给线程置 quitNow，此后所有 QEventLoop::exec() 都直接
    # 返回：测试之间只要有一个用例关了窗口，后面 request_unlock / exec() 之类的
    # 模态循环就全都不再处理事件（Qt 6 已经去掉了这个机制）。这里统一关掉它。
    # 产品本身只有一个事件循环，关闭窗口就是要退出，不受影响。
    from PySide2.QtWidgets import QApplication

    QApplication.setQuitOnLastWindowClosed(False)

    _openssl_folder = _prepare_openssl()
    if _openssl_folder is not None:
        # Qt 用 LoadLibrary 按 PATH 的目录找 DLL，放在最前面优先匹配
        os.environ['PATH'] = str(_openssl_folder) + os.pathsep + os.environ.get('PATH', '')
