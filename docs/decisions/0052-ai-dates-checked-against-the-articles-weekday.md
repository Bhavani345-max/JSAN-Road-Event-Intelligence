# 0052 — AI dates checked against the article's weekday

**Status:** 4 November 2026. Code local, tested, for the user to review and push.
The local database is corrected; production needs no correction (see below).

## Context

On 2 November the read-only review found AI-dated events whose day was off the
weekday the article names. The user asked on 4 November: "fix the AI wrong
weekday dates". The language model is given the publication date and counts
weekdays from it; it sometimes miscounts. Real cases in the local database:

| Event | Article's words | Published | Model's date |
|---|---|---|---|
| EVT-DAB920541B01 | "restrictions on Monday ... between 1 pm and 7 pm" | Mon 2 Nov | Tue 3 Nov |
| EVT-0BD7B3F5E453 | "on Friday night" | Sat 31 Oct | Sun 1 Nov |
| EVT-153580661195 | "for over six hours on Sunday" | Sun 18 Oct (a search engine's time) | Fri 23 Oct |

REI's own date rules (`services/extraction/stated_period.py`) never count
weekdays, so keyword-dated events were not affected.

## Decision

The weekday is the article's own word, so it wins over the model's arithmetic
(`services/extraction/stated_weekday.py`):

- It is read from the period's words ("on Friday night", "From Monday To
  Thursday", "until Thursday evening": an end). When those words are clock
  times only ("between 1 pm and 7 pm"), from the sentence they stand in or the
  one before, then the headline, and only when that text names one weekday.
- Words that also state a calendar date ("on Sunday, October 11"), or "today",
  "tonight", "tomorrow", "yesterday", are left alone: they govern. Plurals
  ("on Sundays") and three or more weekdays are left alone.
- A date already on the named weekday is never moved. A wrong one moves to the
  named weekday nearest the publication day: that day itself when it is the
  weekday; "next" and "last" honoured; otherwise just before or just after the
  publication day, whichever is nearer the model's date (the model reads the
  tense right and miscounts the days). A one-day period moves as a whole.
- When the publication day is a search engine's ("3 days ago"; decision 0038),
  nothing can be counted from it: the wrong dates are removed, never guessed.
- Every change is a note in the reading's `discarded` list, shown in the
  console under "Not used", e.g. "The model dated “on Friday night” Sunday 1 Nov
  2026, which is not a Friday; Friday 30 Oct 2026 is used instead, counted from
  the publication day Saturday 31 Oct 2026".

Where it runs:

- New readings: `services/ai_reading/reading.py` checks the model's period as
  it is read (`ArticleText.publication_day_known`, set by the AI reading
  service from `publication_day_known(record)`).
- Stored readings: `build_event_from_ai` checks them again whenever an event is
  derived, so reprocessing corrects old readings; a checked reading passes
  unchanged. The stored reading stays as the model gave it.
- `backend/cli/recheck_ai_weekdays.py` lists the stored readings off their
  weekday (check only by default) and, with `--apply`, re-derives only those
  events whose dates are the model's (`detection.method` "ai_reading"), each as
  a new version by `ai-reading`; an event a person touched is never changed.

The prompt is unchanged, so nothing is read again and no AI requests are spent.

## Applied

- Local database (backup `backend/.data/backups/rei-2026-11-04-before-weekday-check.db`):
  6 of 47 stored readings with model dates were off. 3 events corrected:
  EVT-DAB920541B01 to Mon 2 Nov 13:00-19:00, EVT-0BD7B3F5E453 to Fri 30 Oct,
  EVT-153580661195 dates removed (search engine's publication day). Not changed:
  one article with no event, and two events whose dates are REI's rules', not the
  model's (EVT-C96EEC4BCF72, EVT-4C0AF7560D0A).
- Production (read-only check inside the API container, with the new check
  loaded in memory): 10 stored readings with model dates, 1 off its weekday, an
  article with no event. No production event needs correcting; after the deploy
  new readings are checked as they are read.

## Verified

`tests/unit/test_stated_weekday.py` (the real cases, the cases left alone,
next/last, both ends of a range, unknown publication day, new and stored
readings) and `tests/api/test_ai_weekday_recheck.py` (the recheck on an in-memory
database: found, corrected as a new version, the stored reading kept, a second
run changes nothing). Existing AI reading tests unchanged and passing.
