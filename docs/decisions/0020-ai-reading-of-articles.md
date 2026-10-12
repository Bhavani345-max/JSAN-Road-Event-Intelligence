# 0020 — A language model reads each news article; REI checks every answer

Date: 2026-10-09. Status: accepted.

## Context

Until now an article became a road event only through the keyword rules
(`services/extraction/keyword_classifier.py`): a weighted phrase list, regex
road names and the OpenStreetMap place list. AI extraction had been held back
since 2 October. On 9 October the user asked for an LLM from OpenRouter
(their key, model `google/gemma-4-26b-a4b-it:free`, reasoning on) to "detect
the intent of every article", answer in JSON, and drive how events are drawn
on the map by intent and reason, without hard-coding.

Constraints found on the day:

- The key is on OpenRouter's free tier: 50 free-model requests a day.
  Rate-limited (429) requests do not count against that.
- About 200 to 400 news articles arrive a day, so one request per article is
  impossible on the free tier.
- The free Gemma models are served only by Google AI Studio and were often
  rate-limited upstream ("temporarily rate-limited upstream").
- The standing rule: never invent road names, times, coordinates or geometry.
- Siasat's terms forbid data mining and AI use of its articles.

## Decision

- **Two passes, batched** (`app/services/ai_reading_service.py`).
  Triage sends about 20 headlines and summaries per request and asks which
  report a road event and of what kind. Only those go to the full pass, a few
  whole articles per request, which returns intent, impact, cause, a one-line
  summary, the city, each place with its role, the period with the article's
  words, the announcing authority and the evidence sentence. A normal day
  needs about 20 requests.
- **Nothing hard-coded.** The prompts, the allowed intents (each must be an
  `EventType`), impacts and place roles, batch sizes and the order in which
  roles locate an event are in `services/ai_reading/config/ai_reading.json`.
  The key, model, fallback models, reasoning switch, daily limit, look-back
  window, excluded sources and tick are settings (`.env`, see `.env.example`).
- **Every answer is checked against the article** (`services/ai_reading/reading.py`).
  A place is kept only if the article contains its name word for word; the
  same for quotes, the authority and the evidence. An intent, impact or role
  outside the configured lists is dropped. Dates are kept only with the
  article's own words: REI's date rules read those words first; the model's
  dates are used only when the rules cannot read them, and are marked so.
  Everything dropped is listed in `detection.ai.discarded`.
- **The model never gives a position.** Places are looked up in the city's
  OpenStreetMap place list exactly as for keyword events and recorded as
  APPROXIMATE. The event sits at the best place by role (closed, affected,
  start of stretch, venue, end of stretch, near), never at a diversion or
  alternative route.
- **Who decides.** A checked full reading that says "road event in this
  city" builds the event (`detection.method = "ai_reading"`), even where the
  keywords found nothing. Where the model says "not a road event" but the
  keywords found one, the keyword event is kept and the model's verdict is
  shown on it: a model's "no" is never an automatic rejection, because the
  console hides rejected events.
- **City scope** is decided by REI, not the model: the city the model names
  must be the source's city (or one of its scope terms); if it names another
  configured city the event is out; if it names none, a place of the event
  must be found in the city's place list.
- **Safety of existing work.** Events are re-derived with the same function
  as reprocessing (`rederive_artifact`), so an event a person has touched is
  never changed and every change is a new version by `ai-reading`.
  Reprocessing reuses the stored reading and never calls the model.
  New events start as VALIDATION_REQUIRED like every text event.
- **Not sent:** structured official records (TfL, Toronto, the Mumbai and
  Bengaluru police listings), manual entries, and the sources in
  `AI_EXCLUDED_SOURCES` (default `siasat,siasat-mumbai`, whose terms forbid it).
- **Budget.** `AI_DAILY_REQUEST_LIMIT` (40) per UTC day, counted in
  `apps/api/.data/ai_usage.json`, and never more than the key's own remaining
  free requests minus 2. Fallback models are tried in turn when the first is
  busy (`AI_FALLBACK_MODELS`, set to the 31B Gemma and NVIDIA Nemotron 3
  Super because Google's free pool is often saturated).
- **Map.** The marker colour is the event type, now the model's intent. For
  the selected event, each located place is drawn with its role: the event's
  colour where the road is closed or affected, green for diversion and
  alternative routes, with a label. The details panel has an "AI reading"
  section: verdict, intent, impact, reason, places and roles with quotes,
  the period, the evidence, and what was discarded.

## Consequences

- Events the keyword list cannot express (unusual wording) can now be found.
  Each is still a lead for a reviewer.
- Free models change and get busy. When none answers, articles wait for the
  next tick (every 5 minutes); nothing is lost. A paid model or a key with
  credits is a settings change only.
- Free OpenRouter endpoints may log prompts. Only public news articles are sent.
- The keyword rules stay: they decide whenever no reading exists (no key,
  limit reached, model busy) and their result is kept on AI events for comparison.

Run by hand: `python apps/api/ai_read.py --status`, `python apps/api/ai_read.py`,
`--max-requests N`, `--days N`, `--all-days`.
