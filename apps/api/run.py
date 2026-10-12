"""Start the REI API for local development:  python apps/api/run.py

Puts the repository root (connectors/, services/, packages/, database/) and
apps/api on the import path, then runs uvicorn with auto-reload.
"""

import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
REPO_ROOT = API_DIR.parents[1]

if __name__ == "__main__":
    import_paths = [str(REPO_ROOT), str(API_DIR)]
    sys.path[:0] = import_paths
    # The reloader starts the app in a child process, which reads PYTHONPATH.
    os.environ["PYTHONPATH"] = os.pathsep.join(
        import_paths + [path for path in [os.environ.get("PYTHONPATH")] if path]
    )

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.environ.get("API_HOST", "127.0.0.1"),
        port=int(os.environ.get("API_PORT", "8000")),
        reload=os.environ.get("API_RELOAD", "true").lower() == "true",
        # Longer than the web app's proxy keeps idle connections, so the proxy
        # never reuses a connection the API has just closed.
        timeout_keep_alive=75,
        reload_dirs=[str(REPO_ROOT / name) for name in ("apps/api", "connectors", "services", "packages", "database")],
    )
