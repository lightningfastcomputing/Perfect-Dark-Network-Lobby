@echo off
setlocal
cd /d "%~dp0"
title Perfect Dark Direct Lobby

where pyw.exe >nul 2>&1
if not errorlevel 1 (
    start "" pyw.exe -3 "%~dp0pd_lobby_tk.py"
    exit /b 0
)

where pythonw.exe >nul 2>&1
if not errorlevel 1 (
    start "" pythonw.exe "%~dp0pd_lobby_tk.py"
    exit /b 0
)

where py.exe >nul 2>&1
if not errorlevel 1 (
    py.exe -3 "%~dp0pd_lobby_tk.py"
    exit /b %errorlevel%
)

where python.exe >nul 2>&1
if not errorlevel 1 (
    python.exe "%~dp0pd_lobby_tk.py"
    exit /b %errorlevel%
)

echo Python 3 was not found.
echo Install Python 3 with Tkinter, then run this file again.
pause
exit /b 1
