@echo off
setlocal
set /p "HOSTIP=Host IP or hostname: "
if not defined HOSTIP exit /b 1
set /p "PORT=Port [27100]: "
if not defined PORT set "PORT=27100"
call "%~dp0PD_DIRECT_LOBBY.bat" join "%HOSTIP%" "%PORT%"
