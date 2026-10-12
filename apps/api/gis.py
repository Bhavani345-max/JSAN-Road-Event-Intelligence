"""GIS Resolution Engine tools (needs GIS_DATABASE_URL and the imported road network):

    python apps/api/gis.py status
    python apps/api/gis.py propose-junction "IIIT Junction" --crossing "DLF road" "Old Bombay Road"
    python apps/api/gis.py junctions
    python apps/api/gis.py resolve EVT-ABC… [EVT-…]
    python apps/api/gis.py resolve --dry-run EVT-ABC…

`propose-junction` records a junction reference as UNCONFIRMED, at the OSM
node where the two named roads meet. It is used for resolution only after a
reviewer confirms it (console or API). `resolve` runs the resolver on the
named events only; results are proposals for human QC.
"""

import argparse
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(API_DIR.parents[1]), str(API_DIR)]

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_db_engine, create_session_factory, run_migrations  # noqa: E402
from app.repositories.events import EventRepository  # noqa: E402
from app.services import gis_service  # noqa: E402
from packages.cities import get_city  # noqa: E402
from services.gis_resolution.network import name_key  # noqa: E402
from services.gis_resolution.postgis import PostGISRoadNetwork, connect  # noqa: E402
from services.gis_resolution.resolver import Mention, OsmGisEngine  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="GIS Resolution Engine tools")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("junctions")
    propose = sub.add_parser("propose-junction")
    propose.add_argument("name")
    propose.add_argument("--crossing", nargs=2, metavar=("ROAD_A", "ROAD_B"), required=True)
    propose.add_argument("--alias", action="append", default=[])
    propose.add_argument("--city", default="hyderabad")
    resolve = sub.add_parser("resolve")
    resolve.add_argument("event_ids", nargs="+")
    resolve.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.gis_database_url:
        sys.exit("GIS_DATABASE_URL is not set (see .env.example).")
    if settings.auto_migrate:
        run_migrations(settings.database_url)
    sessions = create_session_factory(create_db_engine(settings.database_url))

    with connect(settings.gis_database_url) as conn, sessions() as session:
        if args.command == "status":
            network = PostGISRoadNetwork(conn, "hyderabad")
            print(network.version, network.stats())
            return
        if args.command == "junctions":
            for ref in gis_service.junction_refs(session, "hyderabad"):
                print(f"#{ref.ref_id} {ref.name} [{ref.status}] at {ref.position} node {ref.osm_node_id} roads {ref.related_roads}")
            return
        if args.command == "propose-junction":
            city = get_city(args.city)
            network = PostGISRoadNetwork(conn, city.id)
            a, b = args.crossing
            engine = OsmGisEngine(network, bbox=tuple(city.bbox))
            result = engine.intersection(
                Mention(f"{a} and {b}", "review", "crossing", (a, b)), a, network.ways_named(name_key(a)),
                b, network.ways_named(name_key(b)),
            )  # fmt: skip
            if not result.applicable:
                sys.exit(f"Not proposed: {'; '.join(result.reasons) or result.confidence}")
            position = tuple(result.chosen.geometry["coordinates"])
            node = int(result.chosen.reasons[0].rsplit(" ", 1)[-1])
            row = gis_service.propose_junction(
                session, city_id=city.id, name=args.name, aliases=args.alias, position=position,
                osm_node_id=node, related_roads=[a, b],
                source=f"proposed by REI from {network.version}: the OSM node where “{a}” meets “{b}”",
            )  # fmt: skip
            print(f"#{row.junction_id} {row.canonical_name}: {row.status} at {position} (node {node}). "
                  "A reviewer must confirm it before it is used.")
            return
        # resolve
        city = get_city("hyderabad")
        network = PostGISRoadNetwork(conn, city.id)
        engine = gis_service.engine_for(session, city, network)
        for event_id in args.event_ids:
            row = EventRepository(session).get(event_id)
            if row is None:
                print(f"{event_id}: not found")
                continue
            if gis_service.get_network_city(row) is None:
                print(f"{event_id}: no road network for {row.city}; left as it is")
                continue
            report = gis_service.resolve_event(session, row, engine)
            print(f"\n{event_id} — {row.title[:80]}")
            print(f"  changed={report['changed']} applied={report['applied']}")
            for result in report["results"]:
                chosen = result.chosen
                print(f"  • “{result.mention}” ({result.kind}, {result.found_in}): {result.confidence}"
                      + (" ambiguous" if result.ambiguous else "")
                      + (f" → {chosen.method} {chosen.matched_name} {chosen.geometry['type']} {chosen.osm_ids[:3]}" if chosen else "")
                      + (" [APPLIED]" if result.applied else ""))
                for reason in result.reasons + (chosen.reasons if chosen else []):
                    print(f"      - {reason}")
                for alt in result.alternatives[:4]:
                    print(f"      alt: {alt.method} {alt.matched_name} {alt.geometry['type']} {alt.osm_ids[:2]}")
        if args.dry_run:
            session.rollback()
            print("\n(dry run: nothing saved)")
        else:
            session.commit()


if __name__ == "__main__":
    main()
