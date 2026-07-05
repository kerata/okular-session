"""Watch daemon — auto-saves the Okular session whenever open PDFs change."""

from __future__ import annotations

import json
import logging
import signal
import sys
import time
from pathlib import Path

from okular_session.core import STATE_DIR, discover_open_pdfs, session_path

logger = logging.getLogger(__name__)


def _get_saved_files(path: Path) -> set[str]:
    """Return the set of file paths stored in a saved session (empty on error)."""
    try:
        data = json.loads(path.read_text())
        return set(data.get("files", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def run_watch(
    session: str = "default", interval: int = 5, daemon: bool = False
) -> None:
    """Poll Okular every *interval* seconds and auto-save on changes.

    The loop runs until SIGTERM or SIGINT is received.
    """
    path = session_path(session)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    shutdown = False

    def _signal_handler(signum: int, frame: object) -> None:  # noqa: ANN001
        nonlocal shutdown
        logger.info("Received signal %d, shutting down...", signum)
        shutdown = True

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    if not daemon:
        print(f"Watching session {session!r} (polling every {interval}s)…")
        print("Press Ctrl+C to stop.")

    while not shutdown:
        files = discover_open_pdfs()
        current_set = set(files)
        saved_set = _get_saved_files(path)

        if current_set != saved_set:
            if not daemon:
                print(f"[{time.strftime('%H:%M:%S')}] Session changed, saving…")
            data = {"files": files, "saved_at": time.time()}
            path.write_text(json.dumps(data, indent=2))
            if not daemon:
                print(f"  Saved {len(files)} PDF(s).")

        # Sleep in short increments so we respond quickly to signals.
        for _ in range(interval * 10):
            if shutdown:
                break
            time.sleep(0.1)

    if not daemon:
        print("Watch daemon stopped.")
    sys.exit(0)
