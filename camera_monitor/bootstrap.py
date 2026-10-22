"""启动装配：日志、崩溃钩子、单实例、会话退出放行。

从 app.py 拆出来，让"程序怎么起来"这一段能单独读、单独改；
窗口本身的行为仍在 app.py。main() 里对 Window 用的是函数内延迟导入，
避免 app 与本模块互相 import。
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from . import __version__, crash_guard, single_instance, theme
from .autostart import FLAG as AUTOSTART_FLAG

logger = logging.getLogger(__name__)

LOG_FILE = 'camera_monitor.log'
LOG_MAX_BYTES = 1024 * 1024
LOG_BACKUPS = 3


def allow_session_quit(app, window):
    """关机、注销时放行关闭窗口。

    傻瓜模式平时拦着关闭（要密码），这时必须放行，否则机器关不掉。
    Qt 6.8 在 Windows 上收到 WM_QUERYENDSESSION，在 macOS 上走 applicationShouldTerminate
    （⌘Q、程序坞「退出」、注销、关机都走这里），都是先发 commitDataRequest、再关所有窗口。
    所以 macOS 上分不清注销和 ⌘Q，一律放行：现场电脑都是 Windows，macOS 只是开发机。
    """
    app.commitDataRequest.connect(lambda manager: setattr(window, 'authorized_quit', True))


def setup_logging(directory):
    """现场电脑出了问题只能靠日志：写到文件里，满 1 MB 轮换，留 3 份旧的。

    目录建不出来、文件打不开时不写文件，软件照常运行——日志不能反过来让监控起不来。
    返回装上的处理器，没装上返回 None。
    """
    try:
        os.makedirs(directory, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(os.path.join(directory, LOG_FILE),
                                                       maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS, encoding='utf-8')
    except OSError:
        return None
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return handler


def log_startup(argv):
    # 记下是开机自启还是人手打开的：现场说「开机没起来」时先看这一行
    logger.info('Camera Monitor %s 启动%s', __version__, '（开机自启）' if AUTOSTART_FLAG in argv else '')


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Camera Monitor')
    # 要在设好程序名之后取目录，否则会落到没有程序名的公共目录里。
    # 取不到目录时返回空串，拼出来就成了当前目录下的 logs，宁可不写
    data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    log_dir = os.path.join(data, 'logs') if data else ''
    if log_dir:
        setup_logging(log_dir)
    log_startup(sys.argv)
    # 崩溃现场也写进这个目录：打包后没有控制台，闪退只能靠它查
    crash_guard.install(log_dir)
    # 第二个实例直接退出：两套解码线程会把同一批相机挤掉，还会同时写设置和快照
    instance = single_instance.acquire()
    if instance is None:
        QMessageBox.information(None, 'Camera Monitor', '程序已经在运行，请切换到已打开的窗口。')
        return
    from .app import Window   # 延迟导入：app 反过来要用本模块的启动函数
    app.setWindowIcon(QIcon(str(Path(__file__).parent / 'assets' / 'app-icon.png')))
    app.setStyle('Fusion')
    # 夜间值守用的深色皮肤，上次选过就沿用
    theme.apply(app, theme.current())
    window = Window()
    allow_session_quit(app, window)
    window.show()
    sys.exit(app.exec())
