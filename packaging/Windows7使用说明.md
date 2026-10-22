# Camera Monitor · Windows 7 SP1 64 位

这是给 Windows 7 单独构建的版本：界面框架换成 Qt 5（PySide2 5.15.2），
运行库换成 CPython 3.8。功能和 Windows 10/11 版本相同，操作说明也相同，
差别只在系统要求与打包方式。

## 使用成品

将 `CameraMonitor.exe` 复制到目标电脑，双击启动，无需安装 Python。
首次启动会解压内置组件，可能稍慢。请等待主窗口出现。

- 电脑与摄像头连接到同一局域网，点击“搜索设备”。
- 若 Windows 防火墙询问网络权限，允许此程序访问你信任的专用网络；不需要关闭防火墙。
- 已知 IP 但自动搜索不到时，点击左侧“按 IP 添加”，输入摄像头 IPv4 地址，识别后填写连接账号密码。
- 记住密码使用当前 Windows 用户的凭据管理器；不会随 exe 带入其他电脑。
- 视频中断后，每次等待 3 秒重试；停止按钮可取消。
- 顶部的格数选择、双击放大、F11 全屏、大屏密码、机构名称等与 README 中的说明一致。

## 系统要求

- Windows 7 **SP1** 64 位（x64），需要以下系统更新（Windows Update 通常已经装好）：
  - **KB2533623**：`SetDefaultDllDirectories` 等安全加载 API，缺了程序直接起不来；
  - **KB2999226**（Universal C Runtime）：VC++ 2015 运行库依赖的 UCRT。
- 未配置 Windows 代码签名，可能显示未知发布者提示。遵循所在电脑的安全策略。

## 与 Windows 11 版本的区别

| 项目 | Windows 11 版本 | 本版本（Windows 7） |
| --- | --- | --- |
| Python | 3.12 | 3.8（3.9 起不再支持 Windows 7） |
| 界面框架 | PySide6 6.8 / Qt 6 | PySide2 5.15 / Qt 5 |
| 源码 | 同一份 | 同一份，靠 `camera_monitor/qt_compat.py` 适配 Qt 5 |
| 成品名 | `CameraMonitor-Windows11-x64` | `CameraMonitor-Windows7-x64` |

云端下行通道走 `wss`，Qt 5 的 QtNetwork 需要 OpenSSL 1.1：打包时会把
CPython 3.8 自带的 `libssl-1_1-x64.dll` / `libcrypto-1_1-x64.dll` 一并打进 exe，
构建流程里的冒烟测试会检查 `QSslSocket.supportsSsl()`，漏了会直接失败。

## 已知限制

- Qt 5.15 官方支持 Windows 7 SP1；PyInstaller 官方只支持 Windows 8 及以上，
  Windows 7 属于“尽力支持”。构建流程会检查 exe 的系统版本要求（不高于 6.1）
  以及是否引用了 Windows 8 才有的 API，但**最终仍需在 Windows 7 实机上验收**。
- 格式检查与自动测试不能代替实机验收：搜索摄像头、双击连接、多画面播放、
  记住密码后重开、断流重连、停止与关闭窗口都要在现场跑一遍。

## 在 Windows 本地构建

编译电脑要装 **Python 3.8 x64**（要能被 `py -3.8` 找到）并能联网下载依赖。
根目录的 `build-windows.bat` 用的是 Python 3.12，不能用来打这个包；手工执行：

```bat
py -3.8 -m venv .venv-win7
.venv-win7\Scripts\python.exe -m pip install -r packaging\requirements-win7.txt -r packaging\requirements-build-win7.txt
set QT_QPA_PLATFORM=offscreen
.venv-win7\Scripts\python.exe -m unittest discover -s tests -v
set QT_QPA_PLATFORM=
.venv-win7\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath dist-win7 --workpath build-win7 packaging\CameraMonitor-win7.spec
.venv-win7\Scripts\python.exe packaging\verify-windows-win7-exe.py dist-win7\CameraMonitor.exe
.venv-win7\Scripts\python.exe packaging\smoke-windows-exe.py dist-win7\CameraMonitor.exe
```

成品是 `dist-win7\CameraMonitor.exe`，只需要把这一个文件发给使用者。

> 直接跑测试时要让 `tests/` 里的 `from PySide6...` 导入落到 PySide2 上：
> `set CAMERA_MONITOR_ROOT=%CD%` 并把 `%CD%\packaging\win7` 放进 `PYTHONPATH`
> （该目录里的 `sitecustomize.py` 会在解释器启动时启用兼容层）。
>
> 同一个文件还负责给源码环境补上 TLS：Qt 5.15 的 QtNetwork 运行时才去找 OpenSSL 1.1，
> 它会把 CPython 3.8 自带的 `libssl-1_1.dll` / `libcrypto-1_1.dll` 复制成
> `libssl-1_1-x64.dll` / `libcrypto-1_1-x64.dll` 放进 `packaging\win7\openssl\`
> 并加到 `PATH`。少了这一步，`QSslSocket.supportsSsl()` 会是 False，云端下行通道
> （wss）连不上且没有任何报错——`tests/test_launcher.py` 就是靠这条断言拦住的。
> 该目录已被 `.gitignore` 忽略，不需要手工维护。

## GitHub 云端编译

仓库包含 `.github/workflows/windows-win7.yml`。它**只在手动运行时构建**，
改代码 push 到 main 不会自动触发：在仓库 Actions → Build Windows 7 x64 EXE → Run workflow 启动。
流程使用 Windows 云端环境和 Python 3.8 x64：自动运行测试、用 PySide2 打包、
检查 exe 的 x64 架构与 Windows 7 兼容性，并启动主窗口确认视频解码、TLS 与
系统密码存储组件能加载。

成功后，脚本会把 `CameraMonitor-Windows7-x64.zip` 上传到 `v{版本号}` 的 Release
（版本号取自 `camera_monitor/__init__.py`，已存在就覆盖同名资产），可以长期下载。
同一次运行页面的 Artifacts 里也有同样的文件，保留 14 天。
云端无法访问你的内网摄像头，真实搜索、播放和密码保存仍需在目标电脑验收。
