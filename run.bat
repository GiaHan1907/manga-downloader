@echo off
setlocal
set "APP_DIR=%~dp0"

where pyw.exe >nul 2>&1
if not errorlevel 1 (
    start "Manga Downloader" /d "%APP_DIR%" pyw.exe "%APP_DIR%manga_gui.py"
    exit /b 0
)

where pythonw.exe >nul 2>&1
if not errorlevel 1 (
    start "Manga Downloader" /d "%APP_DIR%" pythonw.exe "%APP_DIR%manga_gui.py"
    exit /b 0
)

where py.exe >nul 2>&1
if not errorlevel 1 (
    start "Manga Downloader" /d "%APP_DIR%" py.exe "%APP_DIR%manga_gui.py"
    exit /b 0
)

echo Python was not found. Install Python 3.10+ and try again.
pause
endlocal
