"""Score the console against the user's requirements of 15 October 2026
(R5 as changed on 16 October 2026).

Reads a REI database READ-ONLY, lists events exactly as the API does for the
console's two views (operations: current_upcoming; review queue: validation),
and checks every listed event against the requirements independently of the
rule that listed it:

  R1  Canada, South Africa and Australia are configured.
  R2  At least four working, located sources per new country.
  R3  One point per event: no duplicate rows of one event at one spot, and
      every remaining shared spot is spread apart on the map.
  R4  No expired event is shown (end before now, reported over, or an
      open-ended event read from an article past its days).
  R5  No unconfirmed event is shown (missing a stated start; since 16
      October 2026 a start without an end is allowed).
  R6  No event without a location is shown, and no connected official feed
      lacks locations.

Usage (from backend/):
    ..\\.venv\\Scripts\\python.exe tools/requirements_eval/requirements_eval.py [sqlite path] [--json out.json]
Without a path it reads .data/rei.db.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import hypot
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.repositories.events import EventRepository  # noqa: E402
from app.repositories.sources import SourceRepository  # noqa: E402
from connectors.registry import registered_sources  # noqa: E402
from packages.cities import load_cities  # noqa: E402
from packages.common.time import ensure_utc  # noqa: E402
from services.lifecycle.current import EventListView, open_end_lapsed  # noqa: E402
from services.merging.matcher import normalise  # noqa: E402

NEW_COUNTRIES = {"CA": "Canada", "ZA": "South Africa", "AU": "Australia"}
SOURCES_WANTED = 4
CONSOLE_VIEWS = (EventListView.CURRENT_UPCOMING, EventListView.VALIDATION)
# The map's "same point" (frontend/features/map/geojson.ts SAME_POINT_DIGITS).
SAME_POINT_DIGITS = 6


# --- marker position, as the console computes it (frontend/features/map/geometry.ts) ---


def _line_midpoint(line):
    lengths = [hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(line, line[1:])]
    remaining = sum(lengths) / 2
    for (a, b), length in zip(zip(line, line[1:]), lengths):
        if remaining <= length and length > 0:
            t = remaining / length
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        remaining -= length
    return tuple(line[0])


def _ring_centre(ring):
    open_ring = ring[:-1] or ring
    return (
        sum(p[0] for p in open_ring) / len(open_ring),
        sum(p[1] for p in open_ring) / len(open_ring),
    )


def marker_position(geometry: dict) -> tuple[float, float]:
    kind, coords = geometry["type"], geometry["coordinates"]
    if kind == "Point":
        return (coords[0], coords[1])
    if kind == "LineString":
        return _line_midpoint(coords)
    if kind == "Polygon":
        return _ring_centre(coords[0])
    if kind == "MultiLineString":
        return _line_midpoint(max(coords, key=len))
    if kind == "MultiPolygon":
        return _ring_centre(max((polygon[0] for polygon in coords), key=len))
    raise ValueError(kind)


def point_key(position) -> str:
    return f"{position[0]:.{SAME_POINT_DIGITS}f},{position[1]:.{SAME_POINT_DIGITS}f}"


# --- scoring ---------------------------------------------------------------------------


def evaluate(session: Session, now: datetime, *, before: bool = False) -> dict:
    """`before`: list as the console did before 15 October 2026 (hidden events included)."""
    listed = {}
    for view in CONSOLE_VIEWS:
        rows, _ = EventRepository(session).list(
            view=view, limit=10**9, now=now, include_hidden=before
        )
        for row in rows:
            listed[row.event_id] = (row, view.value)

    expired, unconfirmed, unlocated = [], [], []
    by_point: dict[str, list] = defaultdict(list)
    for event_id, (row, view) in listed.items():
        ended = row.detection and row.detection.get("source_reports_ended")
        lapsed = open_end_lapsed(
            (row.detection or {}).get("method"), row.start_time, row.end_time, now=now
        )
        if row.end_time is not None and ensure_utc(row.end_time) < now or ended or lapsed:
            expired.append(event_id)
        if row.start_time is None:
            unconfirmed.append(event_id)
        if not row.geometry:
            unlocated.append(event_id)
            continue
        by_point[point_key(marker_position(row.geometry))].append(row)

    # Duplicates: rows identical to a reader (same source, type, title, spot and
    # period) shown as separate events. Rows of one source at one spot over one
    # period with different titles (different orders, permits or streets) are
    # separate events; they are counted apart and spread on the map.
    duplicates = 0
    same_period_other_title = 0
    shared_points = 0
    for rows in by_point.values():
        if len(rows) < 2:
            continue
        shared_points += 1
        same = Counter(
            (r.source_id, r.event_type, normalise(r.title), r.start_time, r.end_time) for r in rows
        )
        duplicates += sum(n - 1 for n in same.values() if n > 1)
        loose = Counter((r.source_id, r.event_type, r.start_time, r.end_time) for r in rows)
        same_period_other_title += sum(n - 1 for n in loose.values() if n > 1)
    same_period_other_title -= duplicates
    events_sharing = sum(len(rows) for rows in by_point.values() if len(rows) > 1)

    # Sources per new country: connected (with a connector) and located; working
    # when its last poll succeeded; useful when it has an event on screen.
    registry = {s.definition.source_id: s for s in registered_sources()}
    polled = {s.source_id: s for s in SourceRepository(session).list()}
    shown_per_source = Counter(row.source_id for row, _ in listed.values())
    countries = {}
    configured = {city.country for city in load_cities().values()}
    for code, name in NEW_COUNTRIES.items():
        sources = []
        for source_id, registered in registry.items():
            d = registered.definition
            if d.country != code or registered.create_connector is None:
                continue
            row = polled.get(source_id)
            sources.append(
                {
                    "source_id": source_id,
                    "provides_geometry": d.provides_geometry,
                    "working": bool(row and row.last_success_at and not row.last_error),
                    "events_shown": shown_per_source.get(source_id, 0),
                }
            )
        good = [s for s in sources if s["provides_geometry"] and s["working"] and s["events_shown"]]
        countries[name] = {
            "configured": code in configured,
            "connected": len(sources),
            "working_with_events_shown": len(good),
            "sources": sources,
        }

    official_without_location = [
        sid
        for sid, registered in registry.items()
        if registered.create_connector is not None
        and registered.definition.source_tier == 1
        and not registered.definition.provides_geometry
    ]

    total = len(listed)

    def share_ok(bad: int) -> float:
        return 1.0 if total == 0 else round(1 - bad / total, 4)

    scores = {
        "R1 countries configured": sum(c["configured"] for c in countries.values()) / len(countries),
        "R2 four working located sources per country": round(
            sum(min(c["working_with_events_shown"], SOURCES_WANTED) for c in countries.values())
            / (SOURCES_WANTED * len(countries)),
            4,
        ),
        "R3 no duplicate rows at one spot (identical to a reader)": share_ok(duplicates),
        "R4 no expired event shown": share_ok(len(expired)),
        "R5 no unconfirmed event shown": share_ok(len(unconfirmed)),
        "R6 no unlocated event shown, no unlocated official feed": (
            share_ok(len(unlocated)) if not official_without_location else 0.0
        ),
    }
    return {
        "evaluated_at": now.isoformat(),
        "events_listed": total,
        "listed_by_view": dict(Counter(view for _, view in listed.values())),
        "scores": scores,
        "details": {
            "expired_shown": expired[:20],
            "unconfirmed_shown": unconfirmed[:20],
            "unlocated_shown": unlocated[:20],
            "duplicate_rows_at_one_spot": duplicates,
            "same_source_spot_and_period_other_title": same_period_other_title,
            "spots_shared_by_several_events": shared_points,
            "events_at_shared_spots": events_sharing,
            "official_feeds_without_location": official_without_location,
            "countries": countries,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("database", nargs="?", default=str(BACKEND / ".data" / "rei.db"))
    parser.add_argument("--json", dest="json_out")
    parser.add_argument(
        "--before", action="store_true",
        help="list events as the console did before 15 October 2026, for comparison",
    )
    args = parser.parse_args()
    url = f"sqlite:///file:{Path(args.database).as_posix()}?mode=ro&uri=true"
    engine = create_engine(url)
    with Session(engine) as session:
        result = evaluate(session, datetime.now(timezone.utc), before=args.before)
        session.rollback()
    print(f"Events listed in the console: {result['events_listed']} {result['listed_by_view']}")
    for name, score in result["scores"].items():
        print(f"  {score:7.1%}  {name}")
    details = result["details"]
    print(
        f"  spots shared by several events: {details['spots_shared_by_several_events']} "
        f"({details['events_at_shared_spots']} events; spread apart on the map); of them "
        f"{details['same_source_spot_and_period_other_title']} rows of one source, same spot and "
        "period, different title"
    )
    for country, info in details["countries"].items():
        print(
            f"  {country}: configured={info['configured']} connected={info['connected']} "
            f"working+shown={info['working_with_events_shown']}"
        )
        for source in info["sources"]:
            print(f"      {source}")
    if details["official_feeds_without_location"]:
        print("  official feeds without location:", details["official_feeds_without_location"])
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
