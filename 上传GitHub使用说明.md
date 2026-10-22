# 上传到 GitHub 说明

把这份本地源码上传到自己的 GitHub 仓库，再让 Actions 产出
`CameraMonitor-Windows11-x64`（Windows 11 x64）。

一句话流程：**建一个空仓库 → 关联远程 → push → 在 Actions 里看构建 → 从 Artifacts 下载产物**。

仓库里已经放好两个脚本，不想敲命令的话直接看 [第 10 节：一键脚本](#10-一键脚本upload-to-githubbat)：双击 `upload-to-github.bat`，输入一次仓库地址就行。

---

## 1. 前置条件

| 项目 | 要求 | 本机现状 |
| --- | --- | --- |
| Git | 2.20 以上 | 已安装 2.51.0 |
| GitHub 账号 | 能登录即可 | 需自行准备 |
| 网络 | push 需要能访问 github.com | — |

确认 Git 身份（提交作者信息，**只需要配一次**）：

```powershell
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"
```

本机已配置为 `jianxiashao` / `297407333@qq.com`。查看当前值：

```powershell
git config --global user.name
git config --global user.email
```

---

## 2. 本地仓库已经就绪

这一步已经做完了，不需要重做。当前状态：

| 项目 | 值 |
| --- | --- |
| 分支 | `main`（必须是 main，见第 5 节的说明） |
| 跟踪文件 | 146 个（源码、测试、文档、配置、工作流） |
| 仓库大小 | 约 5 MB（不含构建产物） |
| 远程 | 尚未关联 |

已经就位的两个关键文件：

- `.gitignore`：自动排除虚拟环境、`__pycache__`、`build-win/`、`dist-win/`、
  `*.log`、`test-output.txt`、编辑器目录、`*.key` / `*.crt` 等，**构建产物不会进仓库**。
- `.gitattributes`：固定换行符（`.sh` 用 LF、`.bat` 用 CRLF），避免 macOS 上的
  发布流程因为脚本变成 CRLF 而失败。

上传前自查（输出为空 = 没有漏网的待上传文件）：

```powershell
cd E:\python\CameraMonitor-main
git ls-files --others --exclude-standard   # 现在 git add -A 会收进哪些新文件
git status --short                          # 应为空
```

> 如果以后把项目复制到别的目录重新开始，需要在该目录执行一次
> `git init -b main` 并提交，再按第 3、4 步操作。

---

## 3. 在 GitHub 创建一个空仓库

1. 打开 <https://github.com/new>
2. 填写：
   - **Repository name**：例如 `CameraMonitor`
   - **Description**：可选
   - **Public / Private**：都可以（区别见下方说明）
3. **下面三个勾选项全部不要勾**：
   - Add a README file
   - Add .gitignore
   - Choose a license

   勾了会在远程仓库先产生一个提交，和本地历史没有共同祖先，push 会被拒绝。

创建完成后，页面上会给出仓库地址，形如：

```
https://github.com/<你的用户名>/CameraMonitor.git
```

**Public 还是 Private？**

| | Public | Private |
| --- | --- | --- |
| Actions 额度 | 免费不限 | 每月 2000 分钟免费额度 |
| Windows runner 计费 | — | **按 2 倍分钟计费**（一次构建实际 10–20 分钟 ≈ 扣 20–40 分钟） |
| Artifacts 下载 | 所有人可见 | 仅自己可见 |

只给自己用、不想公开源码，选 Private 即可；注意额度消耗。

---

## 4. 关联远程并推送

```powershell
cd E:\python\CameraMonitor-main
git remote add origin https://github.com/<你的用户名>/CameraMonitor.git
git push -u origin main
```

`-u` 会把 `origin/main` 设为默认上游，以后直接 `git push` 即可。

### 关于认证

首次 push 会弹出 **Git Credential Manager** 窗口（Windows 版 Git 自带），
选择 “Sign in with your browser”，在浏览器里授权即可，之后会自动记住。

如果弹出的是命令行要密码：GitHub 从 2021 年起**不再接受账户密码**，需要 Personal Access Token：

1. GitHub → 右上角头像 → **Settings** → 左侧最下方 **Developer settings**
2. **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**
3. 勾选 `repo` 权限，生成后复制 token
4. 密码处粘贴 token（用户名填 GitHub 用户名）

### 推送之后需要手动运行

Windows 构建设成**只在手动运行时执行**，push 到 main 不会自动跑，
不会消耗 Actions 额度，也不会在 Actions 里堆一串运行记录：

| Workflow | 产物 | 运行环境 |
| --- | --- | --- |
| Build Windows x64 EXE | `CameraMonitor-Windows11-x64` | Python 3.12 + PySide6 / Qt 6 |

推送完成后，到 Actions 页面手动点 Run workflow，见第 5 节。
`Publish desktop release`（macOS 打包 + 正式发布）只在推送 `v*` 标签时运行，见第 7 节。

---

## 5. 手动触发构建并下载产物

1. 打开仓库页面 → 顶部 **Actions**
2. 左侧列表选 **Build Windows x64 EXE**
3. 右侧 **Run workflow** 下拉 → 分支选 `main` → 绿色 **Run workflow**
4. 等待 10–20 分钟（首次要下载 PySide6 依赖，后续有缓存会快一些）
5. 构建成功后，产物有两个地方可以拿：
   - **Release**（长期）：该次运行会自动把 `CameraMonitor-Windows11-x64.zip` 发布到
     `v{版本号}` 的 Release，已存在就覆盖同名资产
   - **Artifacts**（14 天）：这次运行页面最下方的 `CameraMonitor-Windows11-x64`
6. 解压 zip，得到：

   | 文件 | 说明 |
   | --- | --- |
   | `CameraMonitor.exe` | 主程序，复制到目标 Windows 电脑双击即可 |
   | `使用说明.md` | = `packaging/Windows使用说明.md` |
   | `SHA256SUMS.txt` | 校验值，可用 `certutil -hashfile CameraMonitor.exe SHA256` 对比 |
   | `BUILD.txt` | 提交号、运行编号、目标系统、摄像头实机验收状态 |

Release 里的文件长期保留；Artifacts 默认**保留 14 天**，过期后重新跑一次 workflow 即可再生成。

> 为什么不能直接下载 exe 到仓库？
> 几十 MB 的二进制会让仓库越来越臃肿，而且每次改动都要重新提交一次。
> 产物由 Actions 现场生成、走 Release / Artifacts 分发，仓库里只放源码。

### 构建各步骤在做什么

| 步骤 | 作用 |
| --- | --- |
| Install dependencies | 用 `requirements.txt` + `packaging/requirements-build.txt` 装 Python 3.12 依赖 |
| Run regression tests | 跑 `tests/` 全量单元测试（Qt 用 offscreen 模式，不弹窗） |
| Build portable EXE | PyInstaller 按 `packaging/CameraMonitor-windows.spec` 打单文件 exe |
| Verify x64 executable | 检查产物确实是 Windows x64 |
| Test packaged application startup | 真启动 exe，验证主窗口、H.264 解码、TLS（wss）、Windows 凭据后端 |
| Prepare download / Upload | 附上说明、SHA256、构建信息并上传 Artifacts |

---

## 6. 以后的日常流程

改完代码，三行命令即可，构建会自动重跑：

```powershell
cd E:\python\CameraMonitor-main
git add -A
git commit -m "说明这次改了什么"
git push
```

推送**不会**自动开始构建（Windows workflow 只保留手动触发）。
要把新版本发出去，到 Actions 里手动 Run workflow **Build Windows x64 EXE**，
产物会覆盖 `v{版本号}` Release 里的同名 zip。

---

## 7. 可选：打标签发布正式版本

`Publish desktop release` 由 `v*` 标签触发，一次跑完 macOS 打包 + Windows 构建，
最后把两个包一起发布到 Releases 页面：

```powershell
git tag v0.9.1
git push origin v0.9.1
```

| 包 | 来源 |
| --- | --- |
| `CameraMonitor-Windows11-x64.zip` | `windows-exe.yml`（Python 3.12 + Qt 6） |
| `CameraMonitor-macOS-AppleSilicon.zip` | 同一个流程在 macOS runner 上打包 |

手动运行 Windows workflow 时也会把 `CameraMonitor-Windows11-x64.zip` 发布到
`v{版本号}` 的 Release，与打标签发布的文件同名、会互相覆盖（内容相同）。
Release 的说明文字取自 `packaging/RELEASE.md`，发版前记得更新它。

---

## 8. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `remote: Repository not found` | 仓库地址错 / 无权限 / 认证未通过 | 核对用户名与仓库名；重新 `git remote set-url origin <地址>`；确认 token 有 `repo` 权限 |
| `rejected ... fetch first` | 建仓库时勾了 README / .gitignore / license | `git pull --rebase origin main` 后重新 `git push`；或删掉远程仓库重建（保持空仓库） |
| `fatal: remote origin already exists` | 已经关联过远程 | `git remote set-url origin <新地址>` |
| Actions 页面看不到 “Build Windows x64 EXE” | workflow 不在默认分支；或 Actions 被禁用 | 确认仓库默认分支是 `main`（Settings → Branches）；Settings → Actions → General 选 **Allow all actions and reusable workflows** |
| Publish to release 步骤失败，报 403 / `Resource not accessible by integration` | 仓库给 `GITHUB_TOKEN` 的默认权限是只读 | Settings → Actions → General → **Workflow permissions** 选 **Read and write permissions**，保存后重跑 |
| 看不到 `Run workflow` 按钮 | `workflow_dispatch` 只对默认分支显示 | 同上，先确保 workflow 已推送到 `main` |
| 构建卡在 Install dependencies 失败 | 网络/镜像问题 | 重跑一次；日志里会显示具体 pip 报错 |
| Verify x64 executable 失败 | 产物架构不对 | 日志会写明期望的结构与实际值 |
| Test packaged application startup 失败 | exe 起不来（缺 Qt 模块 / TLS / 凭据后端） | 日志会给出具体断言（比如 `TLS backend missing from the bundle`） |
| Run regression tests 失败 | 代码回归 | 运行概览页会直接列出每个失败的测试名和断言 |
| 产物下载按钮是灰的 | 构建未成功或被取消 | 看运行日志；Artifacts 只在成功后有 |

---

## 9. 安全与体积红线

- **不要提交凭据**：`*.key`、`*.crt` 已被 `.gitignore` 排除；任何 token、密码、
  摄像头账号都不要写进代码或文档。
- **不要提交构建产物**：`dist-win/`、`build-win/`、`*.exe`、`*.zip` 都不该进仓库。
- **单个文件不要超过 100 MB**：GitHub 会直接拒绝；仓库长期建议控制在 1 GB 以内。
- **已经误提交了怎么办**：

  ```powershell
  git rm --cached -r dist-win           # 取消跟踪，保留本地文件
  git commit -m "不再跟踪构建产物"
  git push
  ```

  若误提交的是密钥，仅删除文件不够（历史里还在），应立即在对应平台**吊销/重置该密钥**。

---

## 10. 一键脚本：upload-to-github.bat

不想每次敲命令，用仓库根目录的两个脚本：

| 文件 | 作用 |
| --- | --- |
| `upload-to-github.bat` | **双击运行**的入口：切到 UTF-8 代码页，优先用 `pwsh`，没有就用系统自带的 `powershell` |
| `upload-to-github.ps1` | 实际逻辑（已存为 UTF-8 BOM，Windows PowerShell 5.1 下中文不会乱码） |

### 用法

1. 双击 `upload-to-github.bat`
2. 第一次运行会提示粘贴仓库地址，例如 `https://github.com/你的用户名/CameraMonitor.git`
   （地址会写进 git 的 `origin`，**以后运行不再询问**；想换地址在提示里按 `n` 重新输入）
3. 之后全自动，结束时打印 Actions 地址和要去哪里下载 `CameraMonitor-Windows11-x64`

### 脚本会做什么

| 步骤 | 内容 |
| --- | --- |
| 1/4 检查环境 | 确认 `git` 可用；目录不是仓库就 `git init -b main` |
| 2/4 检查待提交内容 | 没配用户名/邮箱就提示输入；有未提交改动就 `git add -A` + 提交（说明默认“更新：<时间>”） |
| 3/4 关联远程仓库 | 读取已记住的地址或提示输入；地址没变就跳过，改了则 `git remote set-url` |
| 4/4 推送到 GitHub | `git push -u origin main`；结束后打印 Actions 链接 |

### 可选参数

```powershell
# 只检查、不推送、不改任何配置（第一次用建议先这样跑一遍）
.\upload-to-github.bat -DryRun

# 直接指定仓库地址，跳过交互
.\upload-to-github.bat -Repository https://github.com/me/CameraMonitor.git

# 自定义本次提交说明
.\upload-to-github.bat -Message "修正摄像头搜索超时"
```

也可以在 PowerShell 里直接跑 `.ps1`：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\upload-to-github.ps1 -DryRun
```

### 安全边界

- **只往 `main` 推**，不会执行 `git push --force`，不会删除远程分支
- 遇到 `[rejected] fetch first`（远程已有 README 之类）会**先询问**，同意后才 `git pull --rebase`
- `-DryRun` 全程只打印将要执行的命令，不写 remote、不提交、不推送
- 脚本本身也是仓库里的普通文件，会被一起提交；换电脑 clone 下来照样能用
