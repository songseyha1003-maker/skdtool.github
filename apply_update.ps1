
Start-Sleep -Seconds 2
Stop-Process -Name "SN_TOOL" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
# Backup existing license.key before extracting
$licBackup = $null
if (Test-Path ".\license.key") {
    $licBackup = [System.IO.File]::ReadAllBytes(".\license.key")
}
Expand-Archive -Path "data\cache\update\update_package.zip" -DestinationPath "." -Force
if ($licBackup -ne $null) {
    [System.IO.File]::WriteAllBytes(".\license.key", $licBackup)
}
Remove-Item -Force "data\cache\update\update_package.zip" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Start-Process "SN_TOOL.exe"
Remove-Item -Force $MyInvocation.MyCommand.Path -ErrorAction SilentlyContinue
