Option Explicit

Dim shell, fso, scriptPath, launcherPath, commandLine
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptPath = WScript.Arguments(0)
launcherPath = ""

' The Python launcher is installed as pyw.exe in the Windows directory.
' It selects the same Python installation as py.exe but never opens a console.
Dim windowsPyw
windowsPyw = shell.ExpandEnvironmentStrings("%WINDIR%") & "\pyw.exe"
If fso.FileExists(windowsPyw) Then
    launcherPath = windowsPyw
End If

If launcherPath = "" Then
    If fso.FileExists("pythonw.exe") Then
        launcherPath = "pythonw.exe"
    End If
End If

If launcherPath = "" Then
    shell.Popup "pyw.exe/pythonw.exe was not found. Install Python 3.10+ and try again.", 5, "Manga Downloader", 16
    WScript.Quit 1
End If

shell.CurrentDirectory = fso.GetParentFolderName(scriptPath)
commandLine = Quote(launcherPath) & " " & Quote(scriptPath)

' Window style 0 = hidden; False = do not wait for the GUI process.
shell.Run commandLine, 0, False

Function Quote(value)
    Quote = Chr(34) & value & Chr(34)
End Function
