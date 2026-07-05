<div align="center">
  <h1>📄 okular-session</h1>
  <p>
    <strong>Save and restore Okular PDF sessions on macOS</strong>
  </p>
  <p>
    <a href="https://github.com/kerata/okular-session/actions">
      <img src="https://github.com/kerata/okular-session/actions/workflows/ci.yml/badge.svg" alt="CI">
    </a>
    <a href="https://pypi.org/project/okular-session/">
      <img src="https://img.shields.io/pypi/v/okular-session" alt="PyPI">
    </a>
    <a href="https://github.com/kerata/okular-session/blob/main/LICENSE">
      <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    </a>
  </p>
</div>

---

## ✨ Features

- **Named sessions** — Save, restore, and organise multiple sets of open PDFs.
- **Fast, native CLI** — Built with `argparse`, zero runtime dependencies.
- **Duplicate‑free** — Automatically deduplicates file paths.
- **Graceful** — Skips missing files during restore.
- **Status & listing** — See what's open and what's saved.
- **Watch daemon** — Auto‑save whenever your session changes.
- **launchd integration** — Run the watch daemon as a background service.
- **pipx‑installable** — Works out of the box with `pipx install okular-session`.

## 📦 Installation

### pipx (recommended)

```bash
pipx install okular-session
```

### Homebrew

```bash
brew install kerata/tap/okular-session
```

Or from a local formula:

```bash
brew install --formula Formula/okular-session.rb
```

## 🚀 Usage

```
usage: okular-session [-h] [--version] [--verbose]
                      {save,restore,list,status,delete,watch,launchd} ...
```

### Commands

| Command | Description |
|---|---|
| `save [session]` | Save the currently open PDFs. Default session name: `default` |
| `restore [session]` | Open all PDFs from a saved session (skips missing files) |
| `list` | List all saved sessions with file counts and timestamps |
| `status` | Show Okular status, open PDFs, and active session |
| `delete <session>` | Delete a saved session |
| `watch [session]` | Watch for changes and auto-save the session |
| `launchd install\|uninstall` | Install or uninstall a background LaunchAgent |

### Examples

```bash
# Save the current set of open PDFs as "work"
okular-session save work

# Restore the "work" session later
okular-session restore work

# List all saved sessions
okular-session list

# Check what's open
okular-session status

# Delete a session
okular-session delete work

# Auto-save every 5 seconds (interactive)
okular-session watch --interval 5

# Install the launchd agent (runs watch at login)
okular-session launchd install
```

## 🔧 How it works

1. **Discover** — `pgrep` finds the Okular PID, then `lsof` lists open files. Only `.pdf` paths are kept.
2. **Save** — Deduplicated paths are written as JSON to `~/.local/state/okular-session/<name>.json`.
3. **Restore** — The JSON is read back; paths that still exist are opened with `open -a Okular`. Missing files are silently skipped.
4. **Watch** — Polls every N seconds and re-saves when the open set changes.
5. **launchd** — A property list is written to `~/Library/LaunchAgents/com.okular-session.plist` and loaded with `launchctl`.

## 📁 Project structure

```
okular-session/
├── src/okular_session/
│   ├── __init__.py      # Version info
│   ├── __main__.py      # python -m okular_session support
│   ├── cli.py           # Argument parser and command dispatch
│   ├── core.py          # Session save/restore/list/delete/status
│   ├── watch.py         # Watch daemon loop
│   └── launchd.py       # launchd plist generation and management
├── tests/
│   └── test_core.py     # Unit tests (pytest)
├── .github/workflows/ci.yml
├── Formula/okular-session.rb  # Homebrew formula
├── pyproject.toml
├── LICENSE
└── README.md
```

## 🧪 Development

```bash
# Clone the repo
git clone https://github.com/kerata/okular-session.git
cd okular-session

# Create a virtualenv and install in editable mode
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Lint
ruff check src/

# Type-check
mypy src/

# Test
pytest -v

# Run locally
okular-session --help
```

## ✅ Roadmap status

| Item | Status |
|---|---|
| Proper package structure | ✅ |
| Named sessions | ✅ |
| `save` / `restore` [session] | ✅ |
| `list` | ✅ |
| `status` | ✅ |
| `delete <session>` | ✅ |
| Watch daemon | ✅ |
| launchd integration | ✅ |
| Unit tests | ✅ |
| GitHub Actions CI | ✅ |
| Homebrew formula | ✅ |
| `pipx install okular-session` | ✅ |
| Nice help output | ✅ |
| Logging | ✅ |
| Versioning | ✅ |
| Type checking (mypy) | ✅ |
| Linting (ruff) | ✅ |

## 📄 License

MIT
