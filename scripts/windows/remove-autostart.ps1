<#
.SYNOPSIS
    Stops JSAN Road Event Intelligence from starting at logon and from being revived.

.DESCRIPTION
    Removes the two scheduled tasks registered by install-autostart.ps1 (and
    the Startup shortcut of the first version, if it is still there). What is
    running now keeps running; stop it with stop-rei.cmd.
#>
foreach ($service in "api", "web") {
    $name = "JSAN REI $service watchdog"
    if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
        Write-Host "Removed: $name"
    }
}
$link = Join-Path ([Environment]::GetFolderPath("Startup")) "JSAN Road Event Intelligence.lnk"
if (Test-Path $link) {
    Remove-Item $link
    Write-Host "Removed: $link"
}
Write-Host "JSAN Road Event Intelligence will no longer start or be revived automatically."
