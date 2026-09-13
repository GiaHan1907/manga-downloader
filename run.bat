@echo off
setlocal

rem Start the GUI through Windows Script Host so it is not a child of this terminal.
wscript.exe "%~dp0launch_gui.vbs" "%~dp0manga_gui.py"

rem Exit immediately; the GUI process is already detached by the VBScript launcher.
endlocal
exit /b 0
