"""Core session management logic."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STATE_DIR = Path.home() / ".local" / "state" / "okular-session"


def _ensure_state_dir() -> None:
    """Create the state directory if it doesn't exist."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_okular_pid() -> str | None:
    """Return the PID of the Okular process, or ``None`` if not running."""
    try:
        r = subprocess.run(
            ["pgrep", "-x", "okular"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        pid = r.stdout.strip()
        return pid if pid else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def discover_open_pdfs() -> list[str]:
    """Discover open PDF files in Okular using ``lsof``.

    Returns a deduplicated list of absolute paths.
    Returns an empty list if Okular is not running or ``lsof`` fails.
    """
    pid = get_okular_pid()
    if not pid:
        return []

    try:
        r = subprocess.run(
            ["lsof", "-F", "fn", "-p", pid],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return []

    seen: set[str] = set()
    files: list[str] = []
    for line in r.stdout.splitlines():
        if line.startswith("n") and line[1:].lower().endswith(".pdf"):
            f = line[1:]
            if f not in seen:
                seen.add(f)
                files.append(f)
    return files


def session_path(name: str) -> Path:
    """Return the filesystem path for a named session (sanitized)."""
    _ensure_state_dir()
    safe_name = name.replace("/", "_").replace("..", "_")
    return STATE_DIR / f"{safe_name}.json"


def save_session(name: str, files: list[str] | None = None) -> int:
    """Save a session, returning the number of files saved.

    If *files* is ``None`` it will be discovered automatically.
    """
    if files is None:
        files = discover_open_pdfs()
    path = session_path(name)
    data: dict[str, Any] = {"files": files, "saved_at": time.time()}
    path.write_text(json.dumps(data, indent=2))
    logger.info("Saved session %r with %d files", name, len(files))
    return len(files)


def restore_session(name: str) -> int:
    """Restore a session, returning the number of files opened.

    Missing files are silently skipped.
    Raises ``FileNotFoundError`` if the session does not exist.
    """
    path = session_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Session {name!r} not found")

    data = json.loads(path.read_text())
    files = [f for f in data.get("files", []) if Path(f).exists()]
    if files:
        subprocess.run(["open", "-a", "Okular", *files], check=True)
    logger.info("Restored session %r with %d files", name, len(files))
    return len(files)


def list_sessions() -> list[dict[str, Any]]:
    """List all saved sessions with metadata."""
    _ensure_state_dir()
    sessions: list[dict[str, Any]] = []
    for p in sorted(STATE_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            sessions.append(
                {
                    "name": p.stem,
                    "files": len(data.get("files", [])),
                    "saved_at": data.get("saved_at"),
                    "modified": p.stat().st_mtime,
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return sessions


def get_status() -> dict[str, Any]:
    """Return a status dict with runtime information."""
    pid = get_okular_pid()
    open_pdfs = discover_open_pdfs() if pid else []
    sessions = list_sessions()

    # Heuristic: detect which saved session matches the current open set,
    # preferring an exact match first.
    current_session: str | None = None
    if open_pdfs:
        current_set = set(open_pdfs)
        for s in sessions:
            path = session_path(s["name"])
            try:
                data = json.loads(path.read_text())
                saved_set = set(data.get("files", []))
                if saved_set == current_set:
                    current_session = s["name"]
                    break
            except (json.JSONDecodeError, OSError):
                continue

    return {
        "okular_running": pid is not None,
        "open_pdfs": len(open_pdfs),
        "sessions": sessions,
        "current_session": current_session,
        "state_dir": str(STATE_DIR),
    }


def delete_session(name: str) -> bool:
    """Delete a session. Returns ``True`` if deleted, ``False`` if not found."""
    path = session_path(name)
    if not path.exists():
        logger.info("Session %r not found for deletion", name)
        return False
    path.unlink()
    logger.info("Deleted session %r", name)
    return True
