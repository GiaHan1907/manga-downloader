Option Explicit

Dim shell, fso, scriptPath, bootstrapPath, pyPath, commandLine
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

If WScript.Arguments.Count < 1 Then
    shell.Popup "The launcher did not receive the GUI script path.", 5, "Manga Downloader", 16
    WScript.Quit 1
End If

scriptPath = WScript.Arguments(0)
bootstrapPath = fso.BuildPath(fso.GetParentFolderName(scriptPath), "detached_gui.py")
pyPath = shell.ExpandEnvironmentStrings("%WINDIR%") & "\py.exe"

If Not fso.FileExists(scriptPath) Then
    shell.Popup "The GUI script was not found:" & vbCrLf & scriptPath, 5, "Manga Downloader", 16
    WScript.Quit 1
End If

If Not fso.FileExists(bootstrapPath) Then
    shell.Popup "The detached launcher was not found:" & vbCrLf & bootstrapPath, 5, "Manga Downloader", 16
    WScript.Quit 1
End If

If Not fso.FileExists(pyPath) Then
    shell.Popup "The Python launcher was not found:" & vbCrLf & pyPath, 5, "Manga Downloader", 16
    WScript.Quit 1
End If

shell.CurrentDirectory = fso.GetParentFolderName(scriptPath)
commandLine = Quote(pyPath) & " " & Quote(bootstrapPath) & " " & Quote(scriptPath)

' Run the bootstrapper hidden and return immediately.
shell.Run commandLine, 0, False

Function Quote(value)
    Quote = Chr(34) & value & Chr(34)
End Function
