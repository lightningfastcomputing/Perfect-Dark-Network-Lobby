@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pyinstaller
if errorlevel 1 pause & exit /b 1
py -m PyInstaller --noconfirm --clean --onefile --windowed --name "Perfect_Dark_Lobby" pd_lobby_tk.py
if errorlevel 1 pause & exit /b 1
copy /y ".\dist\Perfect_Dark_Lobby.exe" ".\Perfect_Dark_Lobby.exe"
echo.
echo Built: %CD%\Perfect_Dark_Lobby.exe
pause
