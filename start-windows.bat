@echo off
rem Run Camera Monitor from source.
rem Needs Python 3.12 or 3.13 (64-bit): PySide6 6.8 / av 17 ship no wheels for 3.14.
setlocal
cd /d "%~dp0"

set "PY="
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=py -3.12"
if defined PY goto have_python
py -3.13 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=py -3.13"
if defined PY goto have_python
goto python_missing

:have_python
set "VENV=.venv"
if not exist "%VENV%\Scripts\python.exe" goto create_venv
rem A .venv built by Python 3.14 cannot install PySide6 6.8; drop it and start over.
"%VENV%\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3,12),(3,13)) else 1)" >nul 2>&1
if not errorlevel 1 goto have_venv
echo Existing .venv was built with an unsupported Python; recreating it...
rmdir /s /q "%VENV%"

:create_venv
%PY% -m venv "%VENV%"
if errorlevel 1 goto fail

:have_venv
"%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto fail
"%VENV%\Scripts\python.exe" -m camera_monitor.app
if errorlevel 1 goto fail
exit /b 0

:python_missing
echo.
echo Python 3.12 or 3.13 (64-bit) is required to run this project.
echo PySide6 6.8 and av 17 do not publish wheels for Python 3.14, which is why
echo "py -3" (your default Python) failed.
echo.
echo Install Python 3.12 from https://www.python.org/downloads/release/python-31210/
echo then check that "py -3.12 -V" prints a version, and run this file again.
echo.
pause
exit /b 1

:fail
echo.
echo Startup failed. See the error above.
echo If a .venv folder already exists from an older Python, delete it and retry.
echo.
pause
exit /b 1
