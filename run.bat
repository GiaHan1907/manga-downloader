@echo off
setlocal
set "APP_DIR=%~dp0"
set "APP_SCRIPT=%APP_DIR%manga_gui.py"

where pyw.exe >nul 2>&1
if not errorlevel 1 (
    start "Manga Downloader" /d "%APP_DIR%" pyw.exe "%APP_SCRIPT%"
    exit /b 0
)

rem Resolve the pythonw.exe belonging to the active Python launcher.
set "PYTHONW_PATH="
for /f "usebackq delims=" %%P in (`py -c "import os,sys; print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))" 2^>nul`) do set "PYTHONW_PATH=%%P"
if defined PYTHONW_PATH if exist "%PYTHONW_PATH%" (
    start "Manga Downloader" /d "%APP_DIR%" "%PYTHONW_PATH%" "%APP_SCRIPT%"
    exit /b 0
)

where pythonw.exe >nul 2>&1
if not errorlevel 1 (
    start "Manga Downloader" /d "%APP_DIR%" pythonw.exe "%APP_SCRIPT%"
    exit /b 0
)

echo pythonw.exe was not found. Install Python 3.10+ and try again.
pause
endlocal
