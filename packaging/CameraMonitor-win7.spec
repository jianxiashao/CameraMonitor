"""Build the Windows 7 portable EXE: CPython 3.8 x64 + PySide2 (Qt 5.15).

Windows 7 跑不了 Qt 6（Qt 6 要求 Windows 10+），所以这里换用 PySide2；
源码通过 camera_monitor/qt_compat.py 继续按 PySide6 的名字导入 Qt。
"""
import atexit
import re
import shutil
import struct
import sys
import sysconfig
import tempfile
from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

if sys.platform != 'win32' or struct.calcsize('P') != 8 or sysconfig.get_platform() != 'win-amd64':
    raise SystemExit('Build requires Windows and x64 Python (not ARM64).')
if sys.version_info[:2] != (3, 8):
    # Python 3.9 起官方不再支持 Windows 7；用别的版本打出来的包在 Win7 上会缺 DLL
    raise SystemExit('Windows 7 build requires CPython 3.8, got %s.' % sys.version.split()[0])

root = Path(SPECPATH).parent
# 与 macOS / Windows 11 一致：版本号只有 camera_monitor/__init__.py 一处
version = re.search(r"__version__\s*=\s*'([^']+)'",
                    (root / 'camera_monitor' / '__init__.py').read_text(encoding='utf-8')).group(1)

metadata = []
for package in ('keyring', 'jaraco.classes', 'importlib_metadata', 'importlib_resources'):
    metadata += copy_metadata(package)

# Qt 5.15 的 QtNetwork 编译时并不链接 OpenSSL，运行时才按名字去找
# libssl-1_1-x64.dll / libcrypto-1_1-x64.dll。缺了它云端下行通道（wss）永远连不上，
# 而且不会有任何报错——冒烟测试也是靠这两个 DLL 才能通过 QSslSocket.supportsSsl()。
# CPython 3.8 自带 OpenSSL 1.1，把它一起打包，并在打包目录里改成 Qt 期望的文件名。
python_dir = Path(sys.base_prefix)
staging = Path(tempfile.mkdtemp(prefix='camera-monitor-openssl-'))
atexit.register(shutil.rmtree, str(staging), True)
openssl = []
for source_name, bundled_name in (('libssl-1_1', 'libssl-1_1-x64.dll'),
                                  ('libcrypto-1_1', 'libcrypto-1_1-x64.dll')):
    found = sorted((python_dir / 'DLLs').glob(source_name + '*.dll')) or sorted(python_dir.glob(source_name + '*.dll'))
    if not found:
        raise SystemExit('Missing %s*.dll next to CPython 3.8; QtNetwork needs it for wss.' % source_name)
    renamed = staging / bundled_name
    shutil.copy2(found[0], renamed)
    openssl.append((str(renamed), '.'))

a = Analysis(
    [str(root / 'packaging' / 'launcher.py')], pathex=[str(root)],
    binaries=openssl,
    datas=metadata + [(str(root / "camera_monitor" / "assets" / "app-icon.png"), "camera_monitor/assets")],
    hiddenimports=['keyring.backends.Windows', 'win32ctypes.pywin32.win32cred',
                   # 源码按 PySide6 的名字导入 Qt，PyInstaller 静态分析看不到 PySide2，
                   # 这里把真正用到的 Qt 子模块全部点名，否则打包出来的程序缺 QtGui/QtWidgets
                   'PySide2.QtCore', 'PySide2.QtGui', 'PySide2.QtWidgets',
                   'PySide2.QtNetwork', 'PySide2.QtWebSockets'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter', 'keyring.backends.macOS', 'PySide2.QtWebEngineCore',
              'PySide2.QtWebEngineWidgets', 'PySide2.QtQml', 'PySide2.QtQuick'],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='CameraMonitor', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    uac_admin=False, icon=str(root / "camera_monitor" / "assets" / "app-icon.ico"),
)
