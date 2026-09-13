Option Explicit

Dim shell, fso, scriptPath, pythonwPath, commandLine
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptPath = WScript.Arguments(0)
pythonwPath = ""

' Resolve the pythonw.exe belonging to the active Python launcher.
On Error Resume Next
Dim process, output
Set process = shell.Exec("py -c ""import os,sys; print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))""")
output = Trim(process.StdOut.ReadAll())
On Error GoTo 0

If fso.FileExists(output) Then
    pythonwPath = output
ElseIf fso.FileExists("pythonw.exe") Then
    pythonwPath = "pythonw.exe"
End If

If pythonwPath = "" Then
    shell.Popup "pythonw.exe was not found. Install Python 3.10+ and try again.", 5, "Manga Downloader", 16
    WScript.Quit 1
End If

shell.CurrentDirectory = fso.GetParentFolderName(scriptPath)
commandLine = Quote(pythonwPath) & " " & Quote(scriptPath)

' Window style 0 = hidden; False = do not wait for the GUI process.
shell.Run commandLine, 0, False

Function Quote(value)
    Quote = Chr(34) & value & Chr(34)
End Function
