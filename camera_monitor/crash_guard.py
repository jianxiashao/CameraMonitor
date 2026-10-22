"""记录崩溃与未捕获异常。

打包成 GUI 程序后没有控制台，stderr 看不到；而 PyAV/FFmpeg 是原生代码，崩起来
连 Python 的 traceback 都没有，现场只表现为"闪退"。这里装两个钩子：

- faulthandler：段错误等致命信号发生时，把各线程的 C 栈直接写进 crash.log；
- sys.excepthook / threading.excepthook：把漏网的 Python 异常也写进日志。

两者都只追加写入，不改变程序行为：日志文件打不开时静默降级，不能反过来影响监控。
"""
import faulthandler
import logging
import os
import sys
import threading

logger = logging.getLogger(__name__)

CRASH_FILE = 'crash.log'

# faulthandler 只在崩溃那一刻写文件，句柄必须一直活着
_handle = None


def _excepthook(exc_type, exc_value, traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, traceback)
        return
    logger.critical('未捕获的异常', exc_info=(exc_type, exc_value, traceback))
    # 开发时在终端里仍然照常打印一份
    if sys.stderr is not None:
        sys.__excepthook__(exc_type, exc_value, traceback)


def _thread_excepthook(args):
    if args.exc_type is SystemExit:
        return
    logger.critical('线程 %s 里未捕获的异常', getattr(args.thread, 'name', '?'),
                    exc_info=(args.exc_type, args.exc_value, args.exc_traceback))


def uninstall():
    """关掉崩溃日志并恢复正常钩子（测试和重复安装时用）。"""
    global _handle
    if _handle is not None:
        try:
            faulthandler.disable()
        except (OSError, ValueError):
            pass
        try:
            _handle.close()
        except OSError:
            pass
        _handle = None


def install(directory):
    """装上两个钩子，返回崩溃日志路径（目录不可用时返回 None）。

    目录建不出来、文件打不开时只装 Python 异常钩子——生产现场宁可少一份 C 栈，
    也不能因为写不了日志就启动失败。
    """
    global _handle
    uninstall()
    path = None
    if directory:
        try:
            os.makedirs(directory, exist_ok=True)
            path = os.path.join(directory, CRASH_FILE)
            _handle = open(path, 'a', buffering=1, encoding='utf-8', errors='replace')
            faulthandler.enable(file=_handle, all_threads=True)
        except (OSError, ValueError):
            _handle = None
            path = None
    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook
    return path
