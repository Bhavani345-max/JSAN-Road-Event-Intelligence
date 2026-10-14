"""Start the REI API for local development:  python backend/run.py

Puts backend/ (app, connectors, services, packages) on the import path, then
runs uvicorn with auto-reload. Migrations are read from database/ at the
repository root.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent

if __name__ == "__main__":
    import_paths = [str(BACKEND_DIR)]
    sys.path[:0] = import_paths
    # The reloader starts the app in a child process, which reads PYTHONPATH.
    os.environ["PYTHONPATH"] = os.pathsep.join(
        import_paths + [path for path in [os.environ.get("PYTHONPATH")] if path]
    )

    import uvicorn

    reload = os.environ.get("API_RELOAD", "true").lower() == "true"
    watched = [str(BACKEND_DIR / name) for name in ("app", "connectors", "services", "packages")]
    watched.append(str(REPO_ROOT / "database"))
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("API_HOST", "127.0.0.1"),
        port=int(os.environ.get("API_PORT", "8000")),
        reload=reload,
        # Longer than the web app's proxy keeps idle connections, so the proxy
        # never reuses a connection the API has just closed.
        timeout_keep_alive=75,
        # Watched folders only matter with reload (uvicorn warns otherwise).
        reload_dirs=watched if reload else None,
    )
