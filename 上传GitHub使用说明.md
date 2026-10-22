# 上传到 GitHub 说明

把这份本地源码上传到自己的 GitHub 仓库，再让 Actions 产出
`CameraMonitor-Windows11-x64`（Windows 10/11）和 `CameraMonitor-Windows7-x64`（Windows 7）。

一句话流程：**建一个空仓库 → 关联远程 → push → 在 Actions 里看构建 → 从 Artifacts 下载产物**。

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
| 提交 | `d0a7350` 扩充 .gitignore、`f4d7d14` 首次提交 |
| 跟踪文件 | 124 个（源码、测试、文档、配置） |
| 仓库大小 | 约 5 MB（不含构建产物） |
| 远程 | 尚未关联 |

已经就位的两个关键文件：

- `.gitignore`：自动排除虚拟环境、`__pycache__`、`build-win7/`、`dist-win7/`、
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

### 推送成功后会立即发生什么

因为 `main` 上有两个 workflow，且它们的 `paths` 都能匹配到本次推送的内容，
GitHub 会**自动并行启动两个构建**：

| Workflow | 产物 | 运行环境 |
| --- | --- | --- |
| Build Windows x64 EXE | `CameraMonitor-Windows11-x64` | Python 3.12 + PySide6 / Qt 6 |
| Build Windows 7 x64 EXE | `CameraMonitor-Windows7-x64` | Python 3.8 + PySide2 / Qt 5.15 |

`Publish desktop release`（macOS 打包 + 正式发布）只在推送 `v*` 标签时运行，
普通 push 不会触发，见第 7 节。

---

## 5. 手动触发构建并下载产物

推送后如果自动构建已经在跑，可以直接跳到第 4 小步。

1. 打开仓库页面 → 顶部 **Actions**
2. 左侧列表选 **Build Windows 7 x64 EXE**
3. 右侧 **Run workflow** 下拉 → 分支选 `main` → 绿色 **Run workflow**
4. 等待 10–20 分钟（首次要下载约 150 MB 的 PySide2，后续有缓存会快一些）
5. 构建成功后，进入这次运行页面，滚动到最下方 **Artifacts** 区域：
   下载 **`CameraMonitor-Windows7-x64`**
6. 解压 zip，得到：

   | 文件 | 说明 |
   | --- | --- |
   | `CameraMonitor.exe` | 主程序，约 73 MB，复制到 Windows 7 机器双击即可 |
   | `使用说明.md` | = `packaging/Windows7使用说明.md` |
   | `SHA256SUMS.txt` | 校验值，可用 `certutil -hashfile CameraMonitor.exe SHA256` 对比 |
   | `BUILD.txt` | 提交号、运行编号、目标系统、Python/Qt 版本 |

Artifacts 默认**保留 14 天**，过期后重新跑一次 workflow 即可再生成。

> 为什么不能直接下载 exe 到仓库？
> 73 MB 的二进制会让仓库越来越臃肿，而且每次改动都要重新提交一次。
> 产物由 Actions 现场生成、走 Artifacts 分发，仓库里只放源码。

### 构建各步骤在做什么

| 步骤 | 作用 |
| --- | --- |
| Install dependencies | 用 `packaging/requirements-win7.txt` + `requirements-build-win7.txt` 装 Python 3.8 依赖 |
| Run regression tests | 跑 `tests/` 全量单元测试（Qt 用 offscreen 模式，不弹窗） |
| Build portable EXE | PyInstaller 按 `packaging/CameraMonitor-win7.spec` 打单文件 exe |
| Verify Windows 7 executable | 检查是否 x64、PE 子系统版本是否 ≤ 6.1、有没有引用 Windows 8 才有的 API |
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

`windows-win7.yml` 的触发路径是 `camera_monitor/**`、`packaging/**`、`tests/**`
和 workflow 自身；只改 `README.md` 这类文档不会触发构建。

想跳过自动触发、等攒够改动再手动跑一次，可以在 commit message 里加 `[skip ci]`。

---

## 7. 可选：打标签发布正式版本

`Publish desktop release` 由 `v*` 标签触发，会跑 macOS 打包 + 取用 Windows 构建，
最后发布到 Releases 页面：

```powershell
git tag v0.9.1
git push origin v0.9.1
```

注意：这个发布流程目前的 `release.yml` 只引用了 `windows-exe.yml`（Windows 11 版）
和 macOS 打包，**Windows 7 版本不会进 Releases**，仍从 Actions 的 Artifacts 获取。
若希望 Win7 版也进正式发布，需要修改 `.github/workflows/release.yml`，把
`windows-win7.yml` 作为额外 job 引入并加入发布清单。

---

## 8. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `remote: Repository not found` | 仓库地址错 / 无权限 / 认证未通过 | 核对用户名与仓库名；重新 `git remote set-url origin <地址>`；确认 token 有 `repo` 权限 |
| `rejected ... fetch first` | 建仓库时勾了 README / .gitignore / license | `git pull --rebase origin main` 后重新 `git push`；或删掉远程仓库重建（保持空仓库） |
| `fatal: remote origin already exists` | 已经关联过远程 | `git remote set-url origin <新地址>` |
| Actions 页面看不到 “Build Windows 7 x64 EXE” | workflow 不在默认分支；或 Actions 被禁用 | 确认仓库默认分支是 `main`（Settings → Branches）；Settings → Actions → General 选 **Allow all actions and reusable workflows** |
| 看不到 `Run workflow` 按钮 | `workflow_dispatch` 只对默认分支显示 | 同上，先确保 workflow 已推送到 `main` |
| 构建卡在 Install dependencies 失败 | 网络/镜像问题 | 重跑一次；日志里会显示具体 pip 报错 |
| Verify Windows 7 executable 失败 | 产物不符合 Win7 要求 | 日志会写明是架构、PE 子系统版本还是 Win8+ API |
| Test packaged application startup 失败 | exe 起不来（缺 Qt 模块 / TLS / 凭据后端） | 日志会给出具体断言（比如 `TLS backend missing from the bundle`） |
| Run regression tests 失败 | 代码回归 | 运行概览页会直接列出每个失败的测试名和断言 |
| 产物下载按钮是灰的 | 构建未成功或被取消 | 看运行日志；Artifacts 只在成功后有 |

---

## 9. 安全与体积红线

- **不要提交凭据**：`*.key`、`*.crt` 已被 `.gitignore` 排除；任何 token、密码、
  摄像头账号都不要写进代码或文档。
- **不要提交构建产物**：`dist-win*/`、`build-win*/`、`*.exe`、`*.zip` 都不该进仓库。
- **单个文件不要超过 100 MB**：GitHub 会直接拒绝；仓库长期建议控制在 1 GB 以内。
- **已经误提交了怎么办**：

  ```powershell
  git rm --cached -r dist-win7          # 取消跟踪，保留本地文件
  git commit -m "不再跟踪构建产物"
  git push
  ```

  若误提交的是密钥，仅删除文件不够（历史里还在），应立即在对应平台**吊销/重置该密钥**。
