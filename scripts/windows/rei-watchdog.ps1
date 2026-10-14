<#
.SYNOPSIS
    Keeps one REI service running: the API (port 8000) or the web console (port 3000).

.DESCRIPTION
    Started by start-rei.cmd, and at Windows logon once install-autostart.ps1
    has been run. The service is started if it is not running. If it stops,
    or stops answering its health check for about a minute, it is started
    again within seconds. A copy already running (started by hand) is watched,
    not replaced. Only one watchdog per service runs at a time.

    Logs: backend\.data\logs\  (watchdog-<service>.log, <service>-<date>.log)

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\windows\rei-watchdog.ps1 -Service api
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("api", "web")]
    [string]$Service
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogDir = Join-Path $Root "backend\.data\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# One watchdog per service, however often start-rei.cmd is run.
$mutex = New-Object System.Threading.Mutex($false, "Local\JSAN-REI-watchdog-$Service")
if (-not $mutex.WaitOne(0)) {
    Write-Host "The REI $Service watchdog is already running."
    exit 0
}

if ($Service -eq "api") {
    $Port = 8000
    $HealthUrl = "http://127.0.0.1:8000/api/health"
    $Command = '"' + (Join-Path $Root ".venv\Scripts\python.exe") + '" backend\run.py'
    $WorkDir = $Root
    # One process instead of a reloader and a worker: less memory, and a
    # restart always runs the current code.
    $env:API_RELOAD = "false"
    # Write log lines as they happen.
    $env:PYTHONUNBUFFERED = "1"
} else {
    $Port = 3000
    $HealthUrl = "http://127.0.0.1:3000/"
    $Command = '"' + (Get-Command npm.cmd -ErrorAction Stop).Source + '" run dev'
    $WorkDir = Join-Path $Root "frontend"
}
$Host.UI.RawUI.WindowTitle = "JSAN REI $Service watchdog - keep this window open"

function Write-Log([string]$Message) {
    $line = "{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $Message
    Write-Host $line
    Add-Content -Path (Join-Path $LogDir "watchdog-$Service.log") -Value $line -Encoding UTF8
}

function Test-Healthy {
    try {
        $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 10
        return $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

# Ids of the processes listening on the port. (In Windows PowerShell 5.1 a single
# connection object has no .Count, so ids are returned, never connection objects.)
function Get-ListenerIds {
    return @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { [int]$_.OwningProcess } | Sort-Object -Unique)
}

function Test-PortHeld {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Stop-Tree([int]$ProcessId) {
    & taskkill.exe /T /F /PID $ProcessId 2>&1 | Out-Null
}

Write-Log "Watchdog started for the $Service (port $Port)."
$delay = 5
while ($true) {
    # A copy already running, started some other way: watch it, do not start a second one.
    if (Test-PortHeld) {
        if (Test-Healthy) {
            Start-Sleep -Seconds 30
            $delay = 5
            continue
        }
        # Held but not answering: it may be starting. Give it time, then free the port.
        Start-Sleep -Seconds 45
        if ((Test-PortHeld) -and -not (Test-Healthy)) {
            Write-Log "Port $Port is held but the $Service does not answer; stopping the stuck process."
            foreach ($id in Get-ListenerIds) { Stop-Tree $id }
            Start-Sleep -Seconds 3
        }
        continue
    }

    $logFile = Join-Path $LogDir ("{0}-{1:yyyy-MM-dd}.log" -f $Service, (Get-Date))
    Write-Log "Starting the $Service."
    $started = Get-Date
    $process = Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/d /c `"$Command >> `"$logFile`" 2>&1`"" `
        -WorkingDirectory $WorkDir -WindowStyle Hidden -PassThru

    $answered = $false
    $misses = 0
    while (-not $process.HasExited) {
        Start-Sleep -Seconds 15
        if (Test-Healthy) {
            $answered = $true
            $misses = 0
            continue
        }
        # Count missed checks once it has answered, or after three minutes of starting.
        if ($answered -or ((Get-Date) - $started).TotalSeconds -gt 180) {
            $misses++
            if ($misses -ge 4) {
                Write-Log "The $Service stopped answering; restarting it."
                Stop-Tree $process.Id
                break
            }
        }
    }

    # A child of the copy that just stopped may still hold the port: stop it,
    # but only a process started after that copy (never one started by hand).
    foreach ($id in Get-ListenerIds) {
        $holder = Get-Process -Id $id -ErrorAction SilentlyContinue
        if ($holder -and $holder.StartTime -ge $started) { Stop-Tree $id }
    }
    $uptime = [int]((Get-Date) - $started).TotalMinutes
    Write-Log "The $Service stopped after $uptime min; starting it again in $delay s. See $logFile."
    Start-Sleep -Seconds $delay
    if ($uptime -ge 10) { $delay = 5 } else { $delay = [Math]::Min($delay * 2, 60) }
}
