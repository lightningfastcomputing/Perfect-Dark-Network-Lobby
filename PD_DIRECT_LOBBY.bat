@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Perfect Dark - Direct Network Lobby

if /I "%~1"=="host" goto HOST
if /I "%~1"=="join" goto JOIN

echo Perfect Dark Direct Lobby Launcher
echo.
echo Usage:
echo   %~nx0 host [PORT] [MAXCLIENTS]
echo   %~nx0 join IP [PORT]
echo.
echo Examples:
echo   %~nx0 host 27100 8
echo   %~nx0 join 192.168.1.50 27100
echo   %~nx0 join 192.168.1.50:27100
echo.
pause
exit /b 1

:HOST
set "PORT=%~2"
set "MAXCLIENTS=%~3"
if not defined PORT set "PORT=27100"
if not defined MAXCLIENTS set "MAXCLIENTS=8"

echo Starting host lobby on UDP port %PORT%...
echo Maximum clients: %MAXCLIENTS%
start "Perfect Dark Host Lobby" /D "%~dp0" "%~dp0pd.x86_64.exe" --portable --skip-intro --host --port %PORT% --maxclients %MAXCLIENTS%
exit /b 0

:JOIN
set "ADDRESS=%~2"
set "PORT=%~3"
if not defined ADDRESS (
    echo ERROR: Supply the host IP address.
    echo Example: %~nx0 join 192.168.1.50 27100
    pause
    exit /b 1
)
if not defined PORT set "PORT=27100"

echo %ADDRESS% | findstr /C:":" >nul
if errorlevel 1 set "ADDRESS=%ADDRESS%:%PORT%"

echo Connecting directly to lobby at %ADDRESS%...
start "Perfect Dark Join Lobby" /D "%~dp0" "%~dp0pd.x86_64.exe" --portable --skip-intro --connect "%ADDRESS%"
exit /b 0
