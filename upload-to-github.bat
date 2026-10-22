@echo off
rem Upload this repository to GitHub. See upload-to-github.ps1 for the details.
rem Double-click to run, or use: upload-to-github.bat -DryRun
setlocal
cd /d "%~dp0"
chcp 65001 >nul

where pwsh >nul 2>nul
if not errorlevel 1 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0upload-to-github.ps1" %*
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0upload-to-github.ps1" %*
)

echo.
pause
