Add-Type -AssemblyName System.Windows.Forms
$coll = New-Object System.Collections.Specialized.StringCollection
$coll.Add("D:\Sal\SN\dist\READY_FOR_GOOGLE_DRIVE\version.json")
$coll.Add("D:\Sal\SN\dist\READY_FOR_GOOGLE_DRIVE\SN_TOOL_UPDATE.zip")
[System.Windows.Forms.Clipboard]::SetFileDropList($coll)
Write-Output "FILES_COPIED_TO_CLIPBOARD_SUCCESS"
