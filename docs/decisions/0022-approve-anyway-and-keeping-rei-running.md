# 0022 — Approving anyway, and keeping REI running

Date: 2026-10-09. Status: accepted.

## Approving anyway

### Context

Approval (decision 0013) requires a start time and a location that is not
approximate. Most news-based events in QC have neither: articles rarely give
a start time, and a named place's position is approximate by definition.
The user, reviewing events, asked to be able to "force approve".

### Decision

- An event in QC_PENDING can be **approved anyway**: `POST
  /api/events/{id}/status` with `"status": "APPROVED", "force": true` and a
  reason of at least 5 characters (422 without one).
- Only the QC checks are overridden (no start time, no location, approximate
  location, unapproved GIS proposal). Which statuses may follow which is not:
  an event must still be confirmed into QC_PENDING first (409 otherwise), and
  only an approval can be forced.
- The record says so: `detection.qc_approval.forced = true` and
  `overridden` lists the checks in the words the console showed; the version
  history entry reads "Approved anyway, overriding: … Reason: …".
- An overridden location check keeps the location's own class: an
  approximate position stays APPROXIMATE (drawn hollow), it does not become
  QC_APPROVED. Forcing an event that meets every check is an ordinary approval.
- Console: under "Approval is blocked", **Approve anyway…** opens a reason
  box; the button stays disabled until a reason is given. An approved-anyway
  event shows the overridden checks and the reason.

## Keeping REI running

### Context

The console showed "The REI API is not reachable" again and again: the API
is a separate process that nothing started or restarted, and runs started
from a Claude Code session were stopped under memory pressure.

### Decision

- `scripts\windows\rei-watchdog.ps1 -Service api|web` keeps one service
  running: started if not running, restarted within seconds if it exits or
  misses four health checks (`/api/health`, `/`); a copy started by hand is
  watched, not replaced; one watchdog per service (named mutex). The API runs
  without auto-reload (one process, less memory).
- Two scheduled tasks for the user ("JSAN REI api watchdog", "JSAN REI web
  watchdog", `install-autostart.ps1`, no administrator rights) run the
  watchdogs hidden (`conhost --headless`) at logon and every 5 minutes with
  "ignore new instance": a watchdog that stops for any reason is back within
  5 minutes. `remove-autostart.ps1` removes them.
- `start-rei.cmd` resumes and runs the tasks (or, without them, starts the
  watchdogs in minimised windows) and opens the console; `stop-rei.cmd`
  pauses the tasks and stops everything.
- The console retries every 5 seconds while the API cannot be reached and
  says so; the message names `start-rei.cmd`.
- Logs: `apps\api\.data\logs\` (`watchdog-<service>.log`, `<service>-<date>.log`).
