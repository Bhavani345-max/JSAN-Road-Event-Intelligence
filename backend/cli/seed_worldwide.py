"""Ingest one current snapshot from every connected live source through the API.

Run after the reviewer exists and the API is running. Set REI_API_URL to seed
a remote deployment; by default the local API is used:
    python backend/cli/seed_worldwide.py
    REI_API_URL=https://api.example.com python backend/cli/seed_worldwide.py
"""

import os
import sys
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
def main() -> int:
    settings = get_settings()
    if not settings.seed_admin_email or not settings.seed_admin_password:
        print("Set SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD in .env, then seed a reviewer first.")
        return 2

    api_url = os.environ.get("REI_API_URL", "http://127.0.0.1:8000").rstrip("/")
    print(f"Connecting to the REI API at {api_url}.")
    failures = 0
    totals = {"fetched": 0, "events_created": 0, "revised": 0}
    try:
        with httpx.Client(base_url=api_url, timeout=180, follow_redirects=True) as client:
            health = client.get("/api/health")
            health.raise_for_status()
            login = client.post(
                "/api/auth/login",
                json={"email": settings.seed_admin_email, "password": settings.seed_admin_password},
            )
            login.raise_for_status()
            sources_response = client.get(
                "/api/sources", params={"integration_status": "CONNECTED"}
            )
            sources_response.raise_for_status()
            source_ids = [
                source["source_id"]
                for source in sources_response.json()
                if source.get("source_class") != "DISCOVERY"
            ]
            if not source_ids:
                print("No connected non-discovery sources are configured.")
                return 1
            print(f"Ingesting a snapshot from {len(source_ids)} connected sources.")
            for index, source_id in enumerate(source_ids, start=1):
                print(f"[{index}/{len(source_ids)}] {source_id}", flush=True)
                response = client.post("/api/ingestion/run", params={"source_id": source_id})
                if response.is_error:
                    failures += 1
                    print(f"  request failed ({response.status_code})", flush=True)
                    continue
                payload = response.json()
                results = payload.get("results", [])
                result = results[0] if results else payload
                for key in totals:
                    totals[key] += int(result.get(key, 0) or 0)
                status = result.get("status", "unknown")
                if status == "failed":
                    failures += 1
                    print(f"  source fetch failed: {result.get('error') or 'no details'}", flush=True)
                else:
                    print(
                        "  "
                        f"{status}; fetched={result.get('fetched', 0)}; "
                        f"events={result.get('events_created', 0)}; revised={result.get('revised', 0)}",
                        flush=True,
                    )
    except httpx.HTTPError as error:
        print(f"Could not reach or authenticate with the REI API: {error}")
        return 1

    print(
        "Snapshot complete: "
        f"fetched={totals['fetched']}, events_created={totals['events_created']}, "
        f"revised={totals['revised']}, source_failures={failures}. "
        "New events remain in the review queue until a reviewer validates them."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
