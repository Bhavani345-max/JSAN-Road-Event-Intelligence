# 0043 — Own profile, theme colour, country flag and country search

**Status:** 28 October 2026. Code local, tested, for the user to push. No database
migration and no Railway setting.

## Context

The user asked (28 October 2026) for: changing the profile details; choosing the
tool's theme colour in the tool; a background colour on the Sign out button; the
country's flag at the top when a country is chosen; and a search box in the
country list. Until now an account's email and password could only be changed with
`backend/cli/update_account_credentials.py` on the server (decision 0032), and no
account could change its name.

## Decision

### Own profile (API)

- `POST /api/auth/profile` (`display_name`, `email`, `current_password`) and
  `POST /api/auth/password` (`current_password`, `new_password`) change **the
  signed-in account only**. No route reaches another account, a role or the
  account's status; extra fields (`role`, `user_id`) are ignored.
- Both accounts may use them, the view-only User too: it is their own account, not
  REI's data. Decision 0032's table still holds: creating accounts, changing roles
  or **others'** passwords has no route. The User still gets 403 on every change to
  REI's data (`require_user`); the new routes use `require_account` (signed in,
  allowed origin, any role).
- A new email or password needs the **current password**. Wrong ones count towards
  the account's sign-in limit (8 in 15 minutes, then 429 for sign-in too), so a
  session left open cannot be used to guess it.
- The browser making the change stays signed in; the account's **other sessions
  end** after a new email or password.
- Names are tidied (spaces) and must be 1–120 characters; emails as in
  `change_account_email` (valid, not another account's); passwords at least 8
  characters.
- Startup seeding is unchanged: an account is never reset, and a changed email
  never adds a third account (one account per role).

### Console

- **Profile and settings** (the round initials button in the header): tabs
  Profile (name, sign-in email; the current password is asked for only when the
  email changes), Password, Theme colour.
- **Theme colour**: JSAN Blue (default), Teal, Green, Indigo, Purple, Graphite. Each
  keeps JSAN Blue's lightness at every step with another hue, so white text keeps
  the same contrast (at least 7:1 on the sidebar; tested). It recolours every
  `brand-*` colour (sidebar, header, buttons, the map's numbered circles and
  country bubbles). Event-type colours on the map do not change. Kept **in this
  browser only** (localStorage `rei-theme`): two people sharing an account keep
  their own, and nothing is stored on the server. The sign-in page keeps its own
  design.
- **Sign out** is a filled button in the theme's colour.
- **Country choice**: a button with the chosen country's **flag** and name (a globe
  for All countries). It opens a list with a **search box**: by name, ISO code
  (CA), a common other name from two letters on (UK, USA, Holland), or a city of
  the country (Toronto finds Canada, named in the row). Arrow keys, Home/End, Enter
  and Escape work; the search box has the focus when it opens.
- Flags come from the `flag-icons` package (7.5.0, MIT), served with the console;
  emoji flags are not used because Windows shows them as two letters.
- On phones (under 640 px) the header has no city box: the sidebar's city buttons
  choose the city, and the header keeps the title, country, profile and Sign out
  without overlapping (checked at 360 and 390 px).

## Tests

`backend/tests/api/test_own_profile.py` (14; two checks removed by mutation were
caught), `frontend/features/theme/themes.test.ts`,
`frontend/features/profile/profile.test.ts`, `frontend/features/cities/cities.test.ts`
(search). Checked in headless Chrome against a throwaway API and database with test
accounts: country search, flag, profile save, email change, wrong and right
password, every theme, reload keeps the theme, phone and laptop widths.

## Production steps (each needs the user's approval)

1. Commit and push; Railway builds both services (`npm ci` installs `flag-icons`).
2. Sign in, open Profile and settings, change the name, and check the header shows
   it. Changing the email or password works the same way, with the current
   password.
