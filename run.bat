@echo off
setlocal

rem Launch the hidden bootstrapper in a separate process, then close this tab.
start "Manga Downloader Launcher" /min "%WINDIR%\System32\wscript.exe" "%~dp0launch_gui.vbs" "%~dp0manga_gui.py"

endlocal
exit
