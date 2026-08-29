"""Start the word-hoard web interface.

Vertical slice step 6. Run:

    .venv/Scripts/python.exe scripts/serve.py

Then open http://127.0.0.1:8000 in a browser.

A script rather than a bare uvicorn command line so there is one way to start
the thing and it is written down. It also pins the host to loopback, which
matters: this application has no authentication of any kind by design, so it
must never be reachable from the network.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordhoard import db  # noqa: E402  (must follow the sys.path fix)

# Loopback only, never 0.0.0.0. There is no login, no session and no access
# control anywhere in this system, because it was designed for one machine in
# one house. Binding to a routable address would publish one person's entire
# review history to the local network.
HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def main() -> int:
    """Check the database exists, then hand off to uvicorn."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Port to listen on (default: {DEFAULT_PORT})")
    parser.add_argument("--reload", action="store_true",
                        help="Restart on code changes. For development.")
    args = parser.parse_args()

    # Fail here with a readable message rather than inside a request handler,
    # where it would surface as a 500 in the browser.
    if not Path(db.DEFAULT_DB_PATH).exists():
        print(f"error: {db.DEFAULT_DB_PATH} does not exist; "
              f"run scripts/init_db.py first", file=sys.stderr)
        return 1

    # Imported here rather than at module scope so that --help works without
    # uvicorn installed, and so the framework stays out of the import path of
    # anything that does not serve HTTP.
    import uvicorn

    print(f"word-hoard on http://{HOST}:{args.port}  (Ctrl+C to stop)")
    uvicorn.run("web.app:app", host=HOST, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
