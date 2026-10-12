<#
.SYNOPSIS
    Keeps JSAN Road Event Intelligence running: starts it at logon and revives it if it stops.

.DESCRIPTION
    Registers two Windows scheduled tasks for your user (no administrator
    rights needed): "JSAN REI api watchdog" and "JSAN REI web watchdog". Each
    runs scripts\windows\rei-watchdog.ps1 hidden (no window to close by
    accident) when you log in, and again every 5 minutes; a watchdog already
    running makes the new one exit at once, so a watchdog that stopped for any
    reason is back within 5 minutes. The watchdog in turn restarts the API or
    the web console within seconds.

    stop-rei.cmd pauses the tasks; start-rei.cmd resumes them.
    Undo with remove-autostart.ps1.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Watchdog = Join-Path $Root "scripts\windows\rei-watchdog.ps1"
$User = "$env:USERDOMAIN\$env:USERNAME"

foreach ($service in "api", "web") {
    $name = "JSAN REI $service watchdog"
    # conhost --headless runs PowerShell with no window at all.
    $action = New-ScheduledTaskAction -Execute "conhost.exe" `
        -Argument "--headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Watchdog`" -Service $service" `
        -WorkingDirectory $Root
    $atLogon = New-ScheduledTaskTrigger -AtLogOn -User $User
    # Every 5 minutes from now on, with no end.
    $every5 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
    $settings = New-ScheduledTaskSettingsSet `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -Hidden
    $principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $name -Action $action -Trigger @($atLogon, $every5) `
        -Settings $settings -Principal $principal -Force `
        -Description "Keeps the JSAN Road Event Intelligence $service running (scripts\windows\rei-watchdog.ps1)" | Out-Null
    Write-Host "Registered: $name"
}

# The Startup-folder shortcut of the first version is replaced by the tasks.
$link = Join-Path ([Environment]::GetFolderPath("Startup")) "JSAN Road Event Intelligence.lnk"
if (Test-Path $link) {
    Remove-Item $link
    Write-Host "Removed the older Startup shortcut (the tasks replace it)."
}
Write-Host "JSAN Road Event Intelligence now starts at logon and is revived within 5 minutes if it stops."
