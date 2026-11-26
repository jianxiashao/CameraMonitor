@echo off
rem Run Camera Monitor from source.
rem Needs 64-bit Python 3.12 or 3.13: PySide6 6.8 / av 17 ship no wheels for 3.14.
setlocal EnableExtensions
cd /d "%~dp0"

set "PY="
rem Prefer the py launcher, then fall back to a python on PATH.
py -3.12 -c "import sys,struct; sys.exit(0 if struct.calcsize('P')==8 else 1)" >nul 2>&1
if not errorlevel 1 set "PY=py -3.12"
if defined PY goto have_python
py -3.13 -c "import sys,struct; sys.exit(0 if struct.calcsize('P')==8 else 1)" >nul 2>&1
if not errorlevel 1 set "PY=py -3.13"
if defined PY goto have_python
python -c "import sys,struct; sys.exit(0 if sys.version_info[:2] in ((3,12),(3,13)) and struct.calcsize('P')==8 else 1)" >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto have_python
goto python_missing

:have_python
rem Reuse an existing environment before creating one. .venv-win is what the
rem build/test docs use; .venv is the runtime-only default.
set "VENV="
if exist ".venv\Scripts\python.exe" set "VENV=.venv"
if not defined VENV if exist ".venv-win\Scripts\python.exe" set "VENV=.venv-win"
if not defined VENV set "VENV=.venv"

if not exist "%VENV%\Scripts\python.exe" goto create_venv
"%VENV%\Scripts\python.exe" -c "import sys,struct; sys.exit(0 if sys.version_info[:2] in ((3,12),(3,13)) and struct.calcsize('P')==8 else 1)" >nul 2>&1
if not errorlevel 1 goto have_venv
echo Existing %VENV% was built with an unsupported Python; recreating it...
rmdir /s /q "%VENV%"
if exist "%VENV%" goto venv_locked

:create_venv
echo Creating %VENV% with %PY%...
%PY% -m venv "%VENV%"
if errorlevel 1 goto venv_failed

:have_venv
set "PYEXE=%CD%\%VENV%\Scripts\python.exe"
rem Dependencies already installed? Skip the network round-trip so an offline
rem machine starts fine and subsequent starts are instant.
"%PYEXE%" -c "import PySide6, av, keyring, requests, defusedxml, psutil" >nul 2>&1
if not errorlevel 1 goto run_app

echo Installing dependencies into %VENV%...
"%PYEXE%" -m pip install --disable-pip-version-check --no-input -r requirements.txt
if errorlevel 1 goto deps_failed

:run_app
echo Starting Camera Monitor from %VENV%...
"%PYEXE%" -m camera_monitor.app
set "CODE=%errorlevel%"
if not "%CODE%"=="0" goto app_failed
exit /b 0

:python_missing
echo.
echo 64-bit Python 3.12 or 3.13 is required to run this project.
echo PySide6 6.8 and av 17 do not publish wheels for Python 3.14.
echo.
echo Install Python 3.12 x64 from:
echo   https://www.python.org/downloads/release/python-31210/
echo Then check that this prints a version:
echo   py -3.12 -V
echo and run this file again.
echo.
pause
exit /b 1

:venv_locked
echo.
echo Could not remove the old "%VENV%" folder.
echo Close any running Camera Monitor / IDE / terminal that is using it,
echo delete the folder manually, then run this file again.
echo.
pause
exit /b 1

:venv_failed
echo.
echo Creating "%VENV%" failed. See the error above.
echo If the folder already exists and is in use, close other Python windows,
echo delete it manually, and retry.
echo.
pause
exit /b 1

:deps_failed
echo.
echo Installing dependencies failed. This is usually network or proxy related.
echo Run the install manually to see the full error:
echo   "%PYEXE%" -m pip install -r requirements.txt
echo If the machine is offline, copy a prepared .venv folder from another
echo Windows 11 x64 machine with the same Python minor version.
echo.
pause
exit /b 1

:app_failed
echo.
echo Camera Monitor exited with code %CODE%.
echo Logs: %LOCALAPPDATA%\Camera Monitor\logs\camera_monitor.log
echo Crash stack (if any): %LOCALAPPDATA%\Camera Monitor\logs\crash.log
echo Run the same command from PowerShell to see the full traceback:
echo   "%PYEXE%" -m camera_monitor.app
echo.
pause
exit /b %CODE%
