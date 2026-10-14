# QC — reserved

Will hold quality-control workflow logic: review queues, assignment, sampling
and second-reviewer approval.

What exists today lives elsewhere: the allowed status changes are in
`services/lifecycle/transitions.py`, review decisions are applied by
`backend/app/services/review_service.py`, and the review buttons are in
`frontend/features/qc`.
