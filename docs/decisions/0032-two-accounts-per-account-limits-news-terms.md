# 0032 — Two accounts, per-account sign-in limits, news feeds whose terms forbid collection

**Status:** accepted in code, 15 October 2026. Not deployed. Every Railway
step below waits for the user's approval.

## Context

1. Decision 0031 limited failed sign-ins per account (8 in 15 minutes) and per
   visitor address (30 in 15 minutes). Tested in production on 15 October
   2026, the visitor address (the last X-Forwarded-For entry) was not one
   visitor's: it named whichever Railway/CDN relay passed the request on. One
   relay's key was locked for 15 minutes, which would lock out every user
   behind that relay.
2. The user asked for exactly two accounts: **Admin** (full access) and
   **User** (signs in and views; changes nothing). Production has one
   account, the admin. There is no registration route or page.
3. The terms of The Hindu and Deccan Chronicle (read 15 October 2026) forbid
   automated collection; Telangana Today, NewsMeter and Mid-day were to be
   reviewed separately and reported, not disconnected silently.

## Decision

### Sign-in limits

- Failed sign-ins are counted **per account only**: 8 in 15 minutes, then
  429 for that account until the window passes. A success clears its
  account's failures. One account's failures never lock out another.
- **No per-visitor limit.** No request header identifies a visitor reliably
  behind Railway's edge, CDN and the console's `/api` proxy, so
  X-Forwarded-For, X-Real-IP and similar headers are not read at all.
- Memory stays bounded: an account whose failures have aged out is forgotten,
  and above 10,000 tracked accounts every aged-out one is swept.
- Unchanged: PBKDF2-SHA256 with 600,000 rounds, HttpOnly session cookie, same-origin check on changes, the same answer for
  a wrong password and an unknown email.
- Passwords need at least **8** characters, lowered from 12 at the user's
  request on 15 October 2026. A random password (from a password manager) is
  advised; one built from words in the account's email is easy to guess.

### Two accounts

- Accounts are created **only** at API startup (or by `cli/seed_user.py`)
  from configuration: `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` for the Admin
  and `SEED_USER_EMAIL`/`SEED_USER_PASSWORD` for the User (role `user`).
- An account is created once and never changed afterwards: a restart never
  resets a password, role or status.
- **One account per role.** When an account already has the role, a changed
  email creates nothing (a warning is logged), so a third account cannot
  appear by accident.
- The User is skipped, with a warning, when only one of its two values is
  set, its email is the admin's, or its password is shorter than 8
  characters. The API still starts.
- No registration, sign-up or user-management route exists. Passwords are
  never logged or printed.

### Roles (enforced by the API; the console only leaves out what the API would refuse)

| | Admin (`admin`) | User (`user`) |
| --- | --- | --- |
| Sign in, view events, map, sources, cities, API docs | yes | yes |
| Review decisions (status, severity, extend, location, merges, GIS), manual events | yes | 403 |
| Run sources (`POST /api/ingestion/run`, "Check" buttons) | yes | 403 |
| Create accounts, change roles or others' passwords | no route exists | no route exists |

The `reviewer` role from decision 0031 stays in code; no account has it.

### News feeds

Disconnected on 15 October 2026 until the publisher gives permission:
`the-hindu`, `the-hindu-bengaluru` and `deccan-chronicle`. They stay
registered with status `TERMS_REVIEW_REQUIRED`, inactive, with no connector
and the quoted terms in their notes. Their stored articles, events, revisions
and audit history are kept and still shown; their parsers stay for
reconnecting.

- **The Hindu** (https://www.thehindu.com/termsofuse/): users may not "use
  robots, spiders, scripts … or otherwise use, access, or collect the
  Content, data or information from the Services using automated means",
  nor use the Content to train AI.
- **Deccan Chronicle** (https://www.deccanchronicle.com/terms-and-condition):
  a "limited license only for purposes of viewing the material"; no
  republishing, no "commercializing", no "data mining, data harvesting, data
  extracting".

Bengaluru now has no connected source: The Hindu Bengaluru was its only one.

### Terms of the three feeds still connected (reported, not changed)

| Feed | Terms found | robots.txt for REI's feed path | Finding |
| --- | --- | --- | --- |
| Telangana Today (`/hyderabad/feed`) | https://telanganatoday.com/terms-and-conditions answers but has no terms text; footer: "© Copyrights 2024 TELANGANA PUBLICATIONS PVT. LTD. All rights reserved." | Allowed for all agents. The whole site is closed to GPTBot, ChatGPT-User and CCBot (AI crawlers). | No written permission or prohibition. All rights reserved; the publisher opposes AI crawling. |
| NewsMeter (`/category/hyderabad/google_feeds.xml`) | No terms page (`/terms`, `/terms-of-use`, `/terms-and-conditions` give 404; none linked) | Allowed for all agents | No terms at all. The feed is named for Google News. |
| Mid-day (`/Resources/midday/rss/mumbai.xml`) | https://www.mid-day.com/terms-and-conditions: viewing or downloading grants "only a limited, nonexclusive license for use solely by you for your own personal use and not for republication, distribution … or other use. No part of any content … may be reproduced in any form or incorporated into any information retrieval system … other than for your personal use" | Allowed for all agents | Personal use only, and storing articles in a retrieval system such as REI is excluded. As restrictive as Deccan Chronicle. |

Recommendation (for the user to decide):

- Disconnect Mid-day in the same way. Mumbai would then have no connected
  source.
- Keep Telangana Today and NewsMeter, and ask both publishers for written
  permission.
- Keep AI reading of articles off in production. It is off today: no
  OpenRouter key is set there. A local `.env` with a key does send article
  text to a model.

## Production steps (each needs the user's approval)

1. Commit and push; Railway deploys the API and the console.
2. Check that sign-in, `/api/auth/me` and the console work for the admin,
   and that 8 wrong passwords on a test email do not affect the admin.
3. To create the User: in the API service's variables, add `SEED_USER_EMAIL`
   (an email different from the admin's) and `SEED_USER_PASSWORD` (a new,
   unique password of at least 8 characters, kept in a password manager).
   Railway redeploys; the log shows `User account … (created)`.
4. Sign in as the User and check: the console opens, review buttons are
   replaced by the view-only note, and a review change answers 403.
5. Optional: remove `SEED_USER_PASSWORD` (and `SEED_ADMIN_PASSWORD`)
   afterwards. The accounts stay; a restart never needs them again.

Tests: `backend/tests/api/test_accounts.py`, `backend/tests/api/test_security.py`,
`backend/tests/unit/test_rss_sources.py`, `frontend/features/auth/permissions.test.ts`.
