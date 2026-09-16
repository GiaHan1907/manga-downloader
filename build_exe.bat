@echo off
setlocal
cd /d "%~dp0"
rem Close an older tray/background instance so PyInstaller can replace the EXE.
taskkill /f /im MangaDownloader.exe >nul 2>&1
if exist "dist\MangaDownloader.exe" del /f /q "dist\MangaDownloader.exe"
if exist "dist\MangaDownloader.exe" (
    echo ERROR: dist\MangaDownloader.exe is still locked. Close it from the system tray and retry.
    exit /b 1
)
rem pathlib is part of Python 3 and the obsolete backport breaks PyInstaller.
py -m pip uninstall -y pathlib >nul 2>&1
py -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1
py convert_icon.py
if errorlevel 1 exit /b 1
py -m PyInstaller --noconfirm --clean MangaDownloader.spec
if errorlevel 1 exit /b 1
echo.
echo Build complete: dist\MangaDownloader.exe
endlocal
