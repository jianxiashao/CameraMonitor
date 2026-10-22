<#
.SYNOPSIS
    把本仓库上传到 GitHub，并告诉你构建产物在哪下载。

.DESCRIPTION
    第一次运行时输入一次仓库地址（例如 https://github.com/你的用户名/CameraMonitor.git），
    脚本会写进 git 的 remote，之后再运行就不用再输入。
    运行过程只做四件事：确认 git 环境、提交未提交的改动、关联远程、push 到 main 分支。
    推送成功后 GitHub Actions 会自动开始构建，脚本最后会打印该去哪下载 exe。

.PARAMETER Repository
    仓库地址。不传时会读取已有的 origin，或者提示你输入一次。

.PARAMETER Message
    有未提交改动时使用的提交说明。不传就用“更新：<时间>”。

.PARAMETER DryRun
    只做检查并打印将要执行的命令，不修改 remote、不 push。第一次用可以先这样试。

.EXAMPLE
    .\upload-to-github.ps1

.EXAMPLE
    .\upload-to-github.ps1 -Repository https://github.com/me/CameraMonitor.git

.EXAMPLE
    .\upload-to-github.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [string]$Repository = '',
    [string]$Message = '',
    [switch]$DryRun
)

# git 会把提示信息写到 stderr，那是正常输出，不应中断脚本；真正的失败点下面显式处理
$ErrorActionPreference = 'Continue'

$script:gitCode = 0

function Invoke-Git {
    # 统一入口：收集 git 的输出（含 stderr），退出码放在 $script:gitCode。
    # 注意函数名不能叫 Git：PowerShell 命令名不区分大小写，会把外部的 git.exe 遮蔽掉。
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    $lines = @(& git @Arguments 2>&1 | ForEach-Object { $_.ToString() })
    $script:gitCode = $LASTEXITCODE
    return $lines
}

function Step($text) {
    Write-Host ''
    Write-Host "== $text" -ForegroundColor Cyan
}

function Ok($text) { Write-Host "   $text" -ForegroundColor Green }

function Note($text) { Write-Host "   $text" -ForegroundColor Gray }

function Warn($text) { Write-Host "   $text" -ForegroundColor Yellow }

function Fail($text, $hint) {
    Write-Host ''
    Write-Host "[失败] $text" -ForegroundColor Red
    if ($hint) { Write-Host "       $hint" -ForegroundColor Yellow }
    Write-Host ''
    exit 1
}

function Get-WebUrl($url) {
    # git@github.com:user/repo.git 和 https://github.com/user/repo.git 都转成网页地址
    if ($url -match '^git@([^:]+):(.+)$') {
        return "https://$($Matches[1])/" + ($Matches[2] -replace '\.git$', '')
    }
    return ($url -replace '\.git$', '')
}

# ---------- 1. 环境检查 ----------

Step '1/4 检查环境'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail '没有找到 git 命令。' '先安装 Git for Windows（https://git-scm.com/download/win），装完重开一个窗口再运行。'
}
Ok 'git 已安装'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $scriptDir

$repoRoot = (Invoke-Git rev-parse --show-toplevel | Select-Object -First 1)
if ($script:gitCode -ne 0 -or -not $repoRoot) {
    $repoRoot = ''
    if ($DryRun) {
        Warn '当前目录还不是 git 仓库（正式运行时会执行 git init -b main）'
    } else {
        Warn '当前目录还不是 git 仓库，正在初始化（分支 main）'
        Invoke-Git init -b main | Out-Null
        $repoRoot = (Invoke-Git rev-parse --show-toplevel | Select-Object -First 1)
    }
}
if ($repoRoot) {
    Set-Location -LiteralPath $repoRoot
    Ok "仓库目录：$repoRoot"
}

# ---------- 2. 提交未提交的改动 ----------

Step '2/4 检查待提交内容'

$hasCommit = $false
if ($repoRoot) {
    Invoke-Git rev-parse --verify HEAD | Out-Null
    $hasCommit = ($script:gitCode -eq 0)
}

if ($hasCommit) {
    $branch = (Invoke-Git rev-parse --abbrev-ref HEAD | Select-Object -First 1)
    if ($branch -and $branch -ne 'main') {
        if ($DryRun) {
            Warn "当前分支是 $branch（正式运行时会改名为 main）"
        } else {
            Invoke-Git branch -M main | Out-Null
            Warn "当前分支是 $branch，已改名为 main（GitHub 上的默认分支必须叫 main）"
        }
    }
}

$name = (Invoke-Git config user.name | Select-Object -First 1)
$email = (Invoke-Git config user.email | Select-Object -First 1)
if (-not $name) {
    if ($DryRun) {
        Warn '没有配置 git 用户名（正式运行时会提示输入）'
    } else {
        $name = Read-Host '   提交要用的名字（会显示在 GitHub 上）'
        if (-not $name) { Fail '没有填写用户名。' '也可以手工执行：git config --global user.name "你的名字"' }
        Invoke-Git config --global user.name $name | Out-Null
    }
}
if (-not $email) {
    if ($DryRun) {
        Warn '没有配置 git 邮箱（正式运行时会提示输入）'
    } else {
        $email = Read-Host '   提交要用的邮箱（建议与 GitHub 账号一致）'
        if (-not $email) { Fail '没有填写邮箱。' '也可以手工执行：git config --global user.email "你的邮箱"' }
        Invoke-Git config --global user.email $email | Out-Null
    }
}
if ($name -and $email) { Ok "提交身份：$name <$email>" }

$changes = @()
if ($repoRoot) {
    $changes = @(Invoke-Git status --porcelain)
}
if ($changes.Count -gt 0) {
    Warn "有 $($changes.Count) 项改动还没提交："
    $changes | Select-Object -First 8 | ForEach-Object { Note $_ }
    if ($changes.Count -gt 8) { Note "…… 还有 $($changes.Count - 8) 项" }

    if (-not $Message) {
        $Message = if ($hasCommit) { '更新：' + (Get-Date -Format 'yyyy-MM-dd HH:mm') } else { '首次提交：CameraMonitor 源码' }
    }

    if ($DryRun) {
        Note "将执行：git add -A 然后 git commit -m `"$Message`""
    } else {
        Invoke-Git add -A | Out-Null
        Invoke-Git commit -q -m $Message | Out-Null
        if ($script:gitCode -ne 0) { Fail '提交失败。' '看一下上面的 git 报错。' }
        Ok "已提交：$Message"
    }
} elseif ($hasCommit) {
    Ok '没有待提交的改动'
} else {
    Warn '仓库里还没有任何提交'
}

# ---------- 3. 关联远程仓库 ----------

Step '3/4 关联远程仓库'

$existing = ''
if ($repoRoot) {
    $existing = (Invoke-Git remote get-url origin | Select-Object -First 1)
    if ($script:gitCode -ne 0) { $existing = '' }
}

$url = $Repository
if (-not $url -and $existing) {
    Ok "已记住的地址：$existing"
    $answer = Read-Host '   直接使用这个地址吗？(Y/n，输入 n 可换成新地址)'
    if ($answer -match '^[nN]') {
        $url = Read-Host '   粘贴仓库地址（例如 https://github.com/你的用户名/CameraMonitor.git）'
    } else {
        $url = $existing
    }
} elseif (-not $url) {
    Write-Host '   还没有关联远程仓库。先到 https://github.com/new 建一个空仓库'
    Write-Host '   （不要勾 README / .gitignore / license），然后把地址粘贴到这里。'
    $url = Read-Host '   仓库地址'
}

$url = "$url".Trim()
if (-not $url) { Fail '没有填写仓库地址。' '' }
if ($url -notmatch '^(https?://|git@|ssh://)') {
    Fail "地址看起来不对：$url" '它应该以 https:// 或 git@ 开头。'
}

$web = Get-WebUrl $url
if ($DryRun) {
    if ($existing) { Note "将执行：git remote set-url origin $url" } else { Note "将执行：git remote add origin $url" }
} else {
    if ($existing) {
        Invoke-Git remote set-url origin $url | Out-Null
        Ok "远程地址已更新：$url"
    } else {
        Invoke-Git remote add origin $url | Out-Null
        Ok "远程地址已设置：$url"
    }
}

# ---------- 4. 推送 ----------

Step '4/4 推送到 GitHub'

if ($DryRun) {
    Note '将执行：git push -u origin main'
    Write-Host ''
    Ok '试运行结束（没有修改任何东西）'
    Write-Host ''
    Write-Host '   去掉 -DryRun 就是正式上传。' -ForegroundColor Gray
    exit 0
}

$output = Invoke-Git push -u origin main
$output | ForEach-Object { Note $_ }
$code = $script:gitCode

if ($code -ne 0) {
    $text = $output -join "`n"
    if ($text -match 'fetch first|non-fast-forward|\[rejected\]') {
        Warn '远程仓库里已经有本地没有的提交（多半是建仓库时勾了 README）。'
        $answer = Read-Host '   现在执行 git pull --rebase origin main 并重试推送吗？(Y/n)'
        if ($answer -notmatch '^[nN]') {
            (Invoke-Git pull --rebase origin main) | ForEach-Object { Note $_ }
            if ($script:gitCode -ne 0) {
                Fail '合并失败，需要手工解决冲突。' '解决冲突后执行 git rebase --continue，再重新运行本脚本。'
            }
            (Invoke-Git push -u origin main) | ForEach-Object { Note $_ }
            if ($script:gitCode -ne 0) { Fail '推送仍然失败。' '看一下上面的 git 报错。' }
            $code = 0
        }
    }
}

if ($code -ne 0) {
    $text = $output -join "`n"
    if ($text -match 'Repository not found|not found|does not exist') {
        Fail '找不到这个仓库。' '核对仓库地址里的用户名和仓库名，确认仓库已经建好、token 有 repo 权限。'
    }
    if ($text -match 'Authentication failed|could not read Username|terminal prompts disabled|Permission denied|403') {
        Fail '认证没有通过。' '重新运行一次，在弹出窗口里登录；或者用 Personal Access Token 代替密码。'
    }
    if ($text -match 'Could not resolve host|unable to access|Failed to connect') {
        Fail '连不上 GitHub。' '检查网络、代理或防火墙设置。'
    }
    Fail '推送失败。' '看一下上面的 git 报错。'
}

Write-Host ''
Ok '推送完成'
Write-Host ''
Write-Host '下一步（推送不会自动构建，需要手动点一下）：' -ForegroundColor Cyan
Write-Host "   1. 打开 $web/actions" -ForegroundColor Gray
Write-Host '   2. 左侧选 Build Windows 7 x64 EXE → 右侧 Run workflow' -ForegroundColor Gray
Write-Host '      （Windows 11 版同理，选 Build Windows x64 EXE）' -ForegroundColor Gray
Write-Host '   3. 构建约 10-20 分钟，跑完产物会自动发布到 Release（长期可下载），' -ForegroundColor Gray
Write-Host '      该次运行页面的 Artifacts 里也有一份（保留 14 天）' -ForegroundColor Gray
Write-Host ''
Write-Host '以后改完代码只要再运行本脚本推送，再到 Actions 手动构建。' -ForegroundColor Gray
