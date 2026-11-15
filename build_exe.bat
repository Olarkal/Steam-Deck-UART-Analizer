@echo off
rem Build RepairFix_UART_Analyzer.exe (Windows, Python 3.8+ from python.org)
rem Optional: put your icon.ico next to this file - it becomes the icon of the exe and the window
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py

set ICONARGS=
if exist icon.ico (
  set ICONARGS=--icon "%~dp0icon.ico" --add-data "%~dp0icon.ico;."
) else (
  echo NOTE: icon.ico not found, building with the default icon
)

rem close running copy, remove old build output and spec (fresh build, fresh icon)
taskkill /f /im RepairFix_UART_Analyzer.exe >nul 2>nul
timeout /t 1 /nobreak >nul
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist RepairFix_UART_Analyzer.spec del /f /q RepairFix_UART_Analyzer.spec
if exist dist\RepairFix_UART_Analyzer.exe (
  echo ERROR: dist\RepairFix_UART_Analyzer.exe is locked. Close the program or antivirus scan and run again.
  pause
  exit /b 1
)

%PY% -m pip install --upgrade pip
%PY% -m pip install pyserial pyinstaller
%PY% -m PyInstaller --clean --noconfirm --onefile --windowed --name RepairFix_UART_Analyzer --hidden-import wiring_images %ICONARGS% deck_uart_analyzer.py
set ERR=%ERRORLEVEL%

rem refresh Windows icon cache so Explorer shows the new icon
ie4uinit.exe -show >nul 2>nul

echo.
if %ERR% neq 0 (echo ERROR: build failed, see messages above) else if exist dist\RepairFix_UART_Analyzer.exe (echo OK: dist\RepairFix_UART_Analyzer.exe) else (echo ERROR: exe not created)
pause
