@echo off
rem ---------------------------------------------------------------------------
rem  JSAN Road Event Intelligence: start everything.
rem
rem  Starts the API (port 8000) and the web console (port 3000), each kept
rem  running by a watchdog that restarts it within seconds if it stops. Safe
rem  to run again: whatever is already running is left alone.
rem
rem  With the scheduled tasks installed (scripts\windows\install-autostart.ps1)
rem  the watchdogs run hidden and are revived within 5 minutes if they stop;
rem  without them, they run in two minimised windows.
rem
rem    start-rei.cmd               start, then open http://localhost:3000
rem    start-rei.cmd --no-browser  start only
rem
rem  Stop everything with stop-rei.cmd. Logs: backend\.data\logs\
rem ---------------------------------------------------------------------------
setlocal
set "ROOT=%~dp0"
set "WATCHDOG=%ROOT%scripts\windows\rei-watchdog.ps1"

schtasks /query /tn "JSAN REI api watchdog" >nul 2>&1
if errorlevel 1 goto :windows

rem Scheduled tasks installed: resume them (stop-rei.cmd pauses them) and run them now.
for %%S in (api web) do (
  schtasks /change /tn "JSAN REI %%S watchdog" /enable >nul
  schtasks /run /tn "JSAN REI %%S watchdog" >nul
)
goto :started

:windows
start "JSAN REI api watchdog" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%WATCHDOG%" -Service api
start "JSAN REI web watchdog" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%WATCHDOG%" -Service web

:started
if /i "%~1"=="--no-browser" goto :done

echo Starting JSAN Road Event Intelligence. The console opens when it is ready...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "for ($i = 0; $i -lt 90; $i++) { try { if ((Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200 -and (Invoke-WebRequest -Uri 'http://127.0.0.1:3000/' -UseBasicParsing -TimeoutSec 10).StatusCode -eq 200) { break } } catch {} ; Start-Sleep -Seconds 2 }; Start-Process 'http://localhost:3000'"

:done
endlocal
