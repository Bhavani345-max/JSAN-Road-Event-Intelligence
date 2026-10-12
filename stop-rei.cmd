@echo off
rem ---------------------------------------------------------------------------
rem  JSAN Road Event Intelligence: stop everything.
rem
rem  Pauses the scheduled tasks (if installed) so nothing is revived, stops the
rem  two watchdogs, then the API on port 8000 and the web console on port 3000.
rem  Start again with start-rei.cmd (which also resumes the tasks).
rem ---------------------------------------------------------------------------
for %%S in (api web) do (
  schtasks /query /tn "JSAN REI %%S watchdog" >nul 2>&1 && (
    schtasks /end /tn "JSAN REI %%S watchdog" >nul 2>&1
    schtasks /change /tn "JSAN REI %%S watchdog" /disable >nul
  )
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name='powershell.exe'\" | Where-Object { $_.CommandLine -like '*-File*rei-watchdog.ps1*' -and $_.ProcessId -ne $PID } | ForEach-Object { & taskkill.exe /T /F /PID $_.ProcessId | Out-Null; 'Stopped a watchdog.' };" ^
  "foreach ($port in 8000, 3000) { Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object { & taskkill.exe /T /F /PID $_.OwningProcess | Out-Null; \"Stopped what was listening on port $port.\" } }"
echo JSAN Road Event Intelligence is stopped.
