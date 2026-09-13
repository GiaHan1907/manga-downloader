@echo off
setlocal
cd /d "%~dp0"

where pyw >nul 2>&1
if %errorlevel%==0 (
    start "" pyw "%~dp0manga_gui.py"
) else (
    pythonw "%~dp0manga_gui.py"
)

endlocal
