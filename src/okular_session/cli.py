"""Command-line interface for okular-session."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from okular_session import __version__
from okular_session.core import (
    delete_session,
    discover_open_pdfs,
    get_okular_pid,
    get_status,
    list_sessions,
    restore_session,
    save_session,
)
from okular_session.launchd import install_launchd, uninstall_launchd
from okular_session.watch import run_watch

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------


def cmd_save(args: argparse.Namespace) -> None:
    files = discover_open_pdfs()
    if not files:
        if get_okular_pid():
            print("No PDFs are currently open in Okular.", file=sys.stderr)
        else:
            print("Okular is not running.", file=sys.stderr)
        sys.exit(1)
    count = save_session(args.session, files)
    print(f"Saved session {args.session!r} with {count} PDF(s).")


def cmd_restore(args: argparse.Namespace) -> None:
    try:
        count = restore_session(args.session)
        print(f"Restored session {args.session!r} ({count} PDF(s)).")
    except FileNotFoundError:
        print(f"Session {args.session!r} not found.", file=sys.stderr)
        sys.exit(1)


def cmd_list(_args: argparse.Namespace) -> None:
    sessions = list_sessions()
    if not sessions:
        print("No sessions saved.")
        return
    print(f"{'Name':<20} {'Files':<8} {'Saved':<25}")
    print("-" * 53)
    for s in sessions:
        ts = ""
        if s["saved_at"]:
            ts = datetime.fromtimestamp(s["saved_at"]).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{s['name']:<20} {s['files']:<8} {ts:<25}")


def cmd_status(_args: argparse.Namespace) -> None:
    status = get_status()
    print(f"Okular running:  {'Yes' if status['okular_running'] else 'No'}")
    print(f"Open PDFs:       {status['open_pdfs']}")
    print(f"Saved sessions:  {len(status['sessions'])}")
    if status["current_session"]:
        print(f"Active session:  {status['current_session']!r}")
    print(f"State directory: {status['state_dir']}")


def cmd_delete(args: argparse.Namespace) -> None:
    if delete_session(args.session):
        print(f"Deleted session {args.session!r}.")
    else:
        print(f"Session {args.session!r} not found.", file=sys.stderr)
        sys.exit(1)


def cmd_watch(args: argparse.Namespace) -> None:
    run_watch(session=args.session, interval=args.interval, daemon=args.daemon)


def cmd_launchd(args: argparse.Namespace) -> None:
    if args.launchd_action == "install":
        install_launchd(verbose=not args.quiet)
    else:
        uninstall_launchd(verbose=not args.quiet)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="okular-session",
        description="Save and restore Okular PDF sessions on macOS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  okular-session save work\n"
            "  okular-session restore work\n"
            "  okular-session list\n"
            "  okular-session status\n"
            "  okular-session delete work\n"
            "  okular-session watch --interval 10\n"
            "  okular-session launchd install\n"
        ),
    )
    ap.add_argument(
        "--version",
        action="version",
        version=f"okular-session {__version__}",
    )
    ap.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    sp = ap.add_subparsers(dest="cmd", required=True)

    # --- save ---
    p = sp.add_parser("save", help="Save the current session")
    p.add_argument(
        "session",
        nargs="?",
        default="default",
        help="Session name (default: %(default)s)",
    )
    p.set_defaults(func=cmd_save)

    # --- restore ---
    p = sp.add_parser("restore", help="Restore a saved session")
    p.add_argument(
        "session",
        nargs="?",
        default="default",
        help="Session name (default: %(default)s)",
    )
    p.set_defaults(func=cmd_restore)

    # --- list ---
    p = sp.add_parser("list", help="List all saved sessions")
    p.set_defaults(func=cmd_list)

    # --- status ---
    p = sp.add_parser("status", help="Show current status")
    p.set_defaults(func=cmd_status)

    # --- delete ---
    p = sp.add_parser("delete", help="Delete a saved session")
    p.add_argument("session", help="Session name to delete")
    p.set_defaults(func=cmd_delete)

    # --- watch ---
    p = sp.add_parser("watch", help="Watch for changes and auto-save")
    p.add_argument(
        "session",
        nargs="?",
        default="default",
        help="Session name (default: %(default)s)",
    )
    p.add_argument(
        "--interval",
        "-i",
        type=int,
        default=5,
        help="Polling interval in seconds (default: %(default)s)",
    )
    p.add_argument(
        "--daemon",
        action="store_true",
        default=False,
        help="Run as daemon (suppress stdout output)",
    )
    p.set_defaults(func=cmd_watch)

    # --- launchd ---
    p = sp.add_parser("launchd", help="Manage launchd integration")
    p.add_argument(
        "launchd_action",
        choices=["install", "uninstall"],
        help="Install or uninstall the launchd agent",
    )
    p.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-error output",
    )
    p.set_defaults(func=cmd_launchd)

    return ap


def main() -> None:
    ap = build_parser()
    args = ap.parse_args()
    _setup_logging(args.verbose)
    try:
        args.func(args)
    except Exception as e:
        logger.debug("Fatal error", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
