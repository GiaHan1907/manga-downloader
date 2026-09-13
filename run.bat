@echo off
setlocal

rem Start Windows Script Host as a separate process, not as a child of this terminal.
start "Manga Downloader Launcher" "%WINDIR%\System32\wscript.exe" "%~dp0launch_gui.vbs" "%~dp0manga_gui.py"

rem Close the cmd.exe tab that was created to run this batch file.
endlocal
exit
