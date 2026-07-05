"""launchd integration — install/uninstall a user LaunchAgent."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

PLIST_LABEL = "com.okular-session"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"


def _get_okular_session_path() -> str:
    """Return the absolute path to the ``okular-session`` executable."""
    resolved = shutil.which("okular-session")
    if resolved:
        return resolved
    # Last-resort fallback: the currently running interpreter.
    import sys

    return sys.argv[0]


def _generate_plist() -> str:
    """Return the launchd plist XML as a string."""
    bin_path = _get_okular_session_path()
    log_dir = Path.home() / "Library" / "Logs" / "okular-session"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{bin_path}</string>
        <string>watch</string>
        <string>--daemon</string>
        <string>--interval</string>
        <string>5</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_dir}/watch.log</string>
    <key>StandardErrorPath</key>
    <string>{log_dir}/watch-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>"""


def install_launchd(verbose: bool = True) -> None:
    """Install the launchd LaunchAgent and load it."""
    plist_dir = PLIST_PATH.parent
    plist_dir.mkdir(parents=True, exist_ok=True)

    log_dir = Path.home() / "Library" / "Logs" / "okular-session"
    log_dir.mkdir(parents=True, exist_ok=True)

    PLIST_PATH.write_text(_generate_plist())
    logger.info("Wrote plist to %s", PLIST_PATH)

    result = subprocess.run(
        ["launchctl", "load", str(PLIST_PATH)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        logger.warning("launchctl load stderr: %s", result.stderr.strip())

    if verbose:
        print(f"Installed launchd agent at {PLIST_PATH}")
        print("The watch daemon will start at login.")
        print(f"To start immediately: launchctl start {PLIST_LABEL}")


def uninstall_launchd(verbose: bool = True) -> None:
    """Unload and remove the launchd LaunchAgent."""
    if not PLIST_PATH.exists():
        if verbose:
            print("launchd agent not installed.")
        return

    result = subprocess.run(
        ["launchctl", "unload", str(PLIST_PATH)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        logger.warning("launchctl unload stderr: %s", result.stderr.strip())

    PLIST_PATH.unlink()
    logger.info("Removed plist at %s", PLIST_PATH)

    if verbose:
        print("Uninstalled launchd agent.")
