# 0013 — QC approval in the console

Date: 2026-10-07. Status: accepted.

## Context

The QC rules for approving an event (services/lifecycle/transitions.py) were
enforced by the API, but the console offered no Approve action: an event in
QC_PENDING could only be sent back to validation or rejected. The user asked
for an Approve button that is enabled only when every QC requirement passes,
says clearly why approval is blocked, and records the decision. Publishing and
customer adapters stay out of scope.

## Decision

- **The rules are unchanged.** `check_transition` still decides. A new
  read-only function, `approval_blockers(event)`, applies the same rules and
  lists every unmet one instead of stopping at the first. A test checks that
  it returns nothing exactly when `check_transition` allows APPROVED, across
  every combination of status, location, start time, location class and GIS
  review.
- **The API states the blockers.** Every event in QC_PENDING carries
  `approval_blockers` (plain sentences); other statuses carry an empty list.
  The console shows that list and never applies rules of its own; the API
  checks again when the approval is sent (HTTP 409 if blocked).
- **The console** shows an Approve button for an event in QC_PENDING, disabled
  while any blocker remains, with an "Approval is blocked" box listing each
  reason. The requirements: a resolved location, a start time, a location that
  is not approximate, and, for a GIS-resolved location, a reviewer's GIS
  approval.
- **The record.** An approval writes `detection.qc_approval` (reviewer, time,
  reason and the event version it created), sets the location class to
  QC_APPROVED, and adds an APPROVED version to the history with the
  reviewer, time and reason. How the location was obtained stays in
  `detection.location`. The reviewer is `local-reviewer` until there is
  authentication.

## Not done

Automatic moves after approval (SCHEDULED, ACTIVE, EXPIRED as dates pass),
publishing, and customer adapters.
