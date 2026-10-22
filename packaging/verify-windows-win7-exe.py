"""Reject artifacts that would not start on Windows 7 SP1 x64.

PyInstaller 只是"应该能在 Windows 7 上跑"，官方支持的是 Windows 8 及以上；
真正的门槛是 exe 里到底引用了哪些系统 API。这里在发布前挡住三种情况：
不是 x64、PE 头要求高于 6.1 的系统、以及引导程序直接引用了 Windows 8 才有的函数。
（onefile 里压缩着 Qt 等 DLL，它们只有在 Windows 7 实机上跑一遍才算验收完成。）
"""
import struct
import sys
from pathlib import Path

import pefile

# Windows 8 / 8.1 / 10 才有的函数：Win7 的 kernel32 里根本没有这些导出
WINDOWS_8_ONLY = frozenset({
    'WaitOnAddress', 'WakeByAddressSingle', 'WakeByAddressAll',
    'GetSystemTimePreciseAsFileTime', 'SetThreadDescription', 'GetThreadDescription',
    'RoInitialize', 'RoUninitialize', 'CreateFile2', 'CopyFile2',
    'PathCchCanonicalizeEx', 'PathCchCombineEx', 'CreateFileMappingFromApp',
    'GetCurrentPackageId', 'GetDpiForWindow', 'GetSystemMetricsForDpi',
    'SetProcessDpiAwarenessContext', 'SetProcessDpiAwareness',
})

path = Path(sys.argv[1])


def fail(message):
    raise SystemExit(message)


with path.open('rb') as stream:
    if stream.read(2) != b'MZ':
        fail('Not a Windows executable')
    stream.seek(0x3c)
    offset = struct.unpack('<I', stream.read(4))[0]
    stream.seek(offset)
    if stream.read(4) != b'PE\0\0':
        fail('Invalid PE signature')
    machine = struct.unpack('<H', stream.read(2))[0]
if machine != 0x8664:
    fail('Expected AMD64/x64, got %#x' % machine)

image = pefile.PE(str(path))
subsystem = (image.OPTIONAL_HEADER.MajorSubsystemVersion, image.OPTIONAL_HEADER.MinorSubsystemVersion)
if subsystem > (6, 1):
    fail('Executable asks for Windows %d.%d, Windows 7 SP1 is 6.1' % subsystem)

imported = {entry.name.decode() for entry in image.DIRECTORY_ENTRY_IMPORT for entry in entry.imports if entry.name}
unsupported = sorted(imported & WINDOWS_8_ONLY)
if unsupported:
    fail('Executable imports Windows 8+ APIs: ' + ', '.join(unsupported))

print('Windows 7 x64 executable verified: %s (%s bytes, subsystem %d.%d)'
      % (path.name, format(path.stat().st_size, ','), subsystem[0], subsystem[1]))
