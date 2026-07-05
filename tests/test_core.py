"""Unit tests for okular-session."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from okular_session.core import (
    STATE_DIR,
    delete_session,
    discover_open_pdfs,
    get_okular_pid,
    get_status,
    list_sessions,
    restore_session,
    save_session,
    session_path,
)

# ---------------------------------------------------------------------------
# session_path
# ---------------------------------------------------------------------------


def test_session_path_default() -> None:
    p = session_path("default")
    assert p.name == "default.json"
    assert p.parent == STATE_DIR


def test_session_path_sanitizes_name() -> None:
    p = session_path("../foo")
    # ".." replaced with "_", so "../foo" -> "__foo.json"
    assert p.name == "__foo.json"


def test_session_path_creates_state_dir() -> None:
    with patch.object(Path, "mkdir") as mock_mkdir:
        session_path("test")
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# get_okular_pid
# ---------------------------------------------------------------------------


class TestGetOkularPid:
    @patch("okular_session.core.subprocess.run")
    def test_running(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="1234\n", returncode=0)
        assert get_okular_pid() == "1234"

    @patch("okular_session.core.subprocess.run")
    def test_not_running(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="\n", returncode=0)
        assert get_okular_pid() is None

    @patch("okular_session.core.subprocess.run", side_effect=FileNotFoundError)
    def test_pgrep_not_found(self, mock_run: MagicMock) -> None:
        assert get_okular_pid() is None

    @patch(
        "okular_session.core.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="pgrep", timeout=5),
    )
    def test_timeout(self, mock_run: MagicMock) -> None:
        assert get_okular_pid() is None


# ---------------------------------------------------------------------------
# discover_open_pdfs
# ---------------------------------------------------------------------------


class TestDiscoverOpenPdfs:
    @patch("okular_session.core.get_okular_pid", return_value="1234")
    @patch("okular_session.core.subprocess.run")
    def test_with_pdfs(self, mock_run: MagicMock, mock_pid: MagicMock) -> None:
        lsof_output = (
            "n/Users/user/doc1.pdf\nn/Users/user/doc2.pdf\nn/Users/user/notes.txt\n"
        )
        mock_run.return_value = MagicMock(stdout=lsof_output, returncode=0)
        result = discover_open_pdfs()
        assert result == ["/Users/user/doc1.pdf", "/Users/user/doc2.pdf"]

    @patch("okular_session.core.get_okular_pid", return_value=None)
    def test_okular_not_running(self, mock_pid: MagicMock) -> None:
        assert discover_open_pdfs() == []

    @patch("okular_session.core.get_okular_pid", return_value="1234")
    @patch("okular_session.core.subprocess.run", side_effect=FileNotFoundError)
    def test_lsof_not_found(self, mock_run: MagicMock, mock_pid: MagicMock) -> None:
        assert discover_open_pdfs() == []

    @patch("okular_session.core.get_okular_pid", return_value="1234")
    @patch("okular_session.core.subprocess.run")
    def test_duplicates_removed(self, mock_run: MagicMock, mock_pid: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="n/doc.pdf\nn/doc.pdf\n", returncode=0)
        result = discover_open_pdfs()
        # lsof returns paths starting with /
        assert result == ["/doc.pdf"]

    @patch("okular_session.core.get_okular_pid", return_value="1234")
    @patch(
        "okular_session.core.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="lsof", timeout=10),
    )
    def test_timeout(self, mock_run: MagicMock, mock_pid: MagicMock) -> None:
        assert discover_open_pdfs() == []

    @patch("okular_session.core.get_okular_pid", return_value="1234")
    @patch("okular_session.core.subprocess.run")
    def test_case_insensitive_ext(
        self, mock_run: MagicMock, mock_pid: MagicMock
    ) -> None:
        mock_run.return_value = MagicMock(
            stdout="n/file.PDF\nn/file2.Pdf\n", returncode=0
        )
        result = discover_open_pdfs()
        # lsof returns paths starting with /
        assert result == ["/file.PDF", "/file2.Pdf"]


# ---------------------------------------------------------------------------
# save_session
# ---------------------------------------------------------------------------


class TestSaveSession:
    @patch("okular_session.core.session_path")
    def test_save_with_files(self, mock_path: MagicMock) -> None:
        mock_path.return_value = Path("/fake/default.json")
        with patch.object(Path, "write_text") as mock_write:
            count = save_session("default", ["a.pdf", "b.pdf"])
            assert count == 2
            written = json.loads(mock_write.call_args[0][0])
            assert written["files"] == ["a.pdf", "b.pdf"]
            assert "saved_at" in written

    @patch("okular_session.core.discover_open_pdfs", return_value=["x.pdf"])
    @patch("okular_session.core.session_path")
    def test_save_auto_discovers(
        self,
        mock_path: MagicMock,
        mock_discover: MagicMock,
    ) -> None:
        mock_path.return_value = Path("/fake/test.json")
        with patch.object(Path, "write_text"):
            count = save_session("test")
            assert count == 1

    @patch("okular_session.core.session_path")
    def test_save_empty_files(self, mock_path: MagicMock) -> None:
        mock_path.return_value = Path("/fake/empty.json")
        with patch.object(Path, "write_text") as mock_write:
            count = save_session("empty", [])
            assert count == 0
            written = json.loads(mock_write.call_args[0][0])
            assert written["files"] == []


# ---------------------------------------------------------------------------
# restore_session
# ---------------------------------------------------------------------------


class TestRestoreSession:
    @patch("okular_session.core.session_path")
    @patch("okular_session.core.subprocess.run")
    def test_restore_existing_files(
        self,
        mock_run: MagicMock,
        mock_path: MagicMock,
    ) -> None:
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.return_value = json.dumps(
            {"files": ["/tmp/a.pdf", "/tmp/b.pdf"]}
        )
        with patch("okular_session.core.Path.exists", return_value=True):
            count = restore_session("work")
            assert count == 2
            mock_run.assert_called_once()
            assert mock_run.call_args[0][0] == [
                "open",
                "-a",
                "Okular",
                "/tmp/a.pdf",
                "/tmp/b.pdf",
            ]

    @patch("okular_session.core.session_path")
    def test_restore_missing_session(self, mock_path: MagicMock) -> None:
        mock_path.return_value.exists.return_value = False
        with pytest.raises(FileNotFoundError):
            restore_session("ghost")

    @patch("okular_session.core.session_path")
    @patch("okular_session.core.subprocess.run")
    def test_restore_ignores_missing_files(
        self,
        mock_run: MagicMock,
        mock_path: MagicMock,
    ) -> None:
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.return_value = json.dumps(
            {"files": ["/tmp/exists.pdf", "/tmp/missing.pdf"]}
        )

        # Return True for first file, False for second — in order of iteration
        with patch("okular_session.core.Path.exists") as mock_exists:
            mock_exists.side_effect = [True, False]
            count = restore_session("work")
            assert count == 1
            mock_run.assert_called_once()
            assert mock_run.call_args[0][0] == [
                "open",
                "-a",
                "Okular",
                "/tmp/exists.pdf",
            ]


# ---------------------------------------------------------------------------
# list_sessions
# ---------------------------------------------------------------------------


class TestListSessions:
    @patch("okular_session.core.STATE_DIR")
    def test_no_sessions(self, mock_dir: MagicMock) -> None:
        mock_dir.glob.return_value = []
        assert list_sessions() == []

    @patch("okular_session.core.STATE_DIR")
    def test_with_sessions(self, mock_dir: MagicMock) -> None:
        p1 = MagicMock(spec=Path)
        p1.stem = "work"
        p1.read_text.return_value = json.dumps(
            {"files": ["a.pdf", "b.pdf"], "saved_at": 1000.0}
        )
        type(p1.stat.return_value).st_mtime = 1000.0

        mock_dir.glob.return_value = [p1]
        sessions = list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["name"] == "work"
        assert sessions[0]["files"] == 2
        assert sessions[0]["saved_at"] == 1000.0

    @patch("okular_session.core.STATE_DIR")
    def test_skips_corrupted_files(self, mock_dir: MagicMock) -> None:
        p = MagicMock(spec=Path)
        p.stem = "bad"
        p.read_text.return_value = "not-json"
        mock_dir.glob.return_value = [p]
        assert list_sessions() == []


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


class TestGetStatus:
    @patch("okular_session.core.get_okular_pid", return_value="1234")
    @patch("okular_session.core.discover_open_pdfs", return_value=["a.pdf"])
    @patch("okular_session.core.list_sessions", return_value=[])
    def test_okular_running(
        self,
        mock_list: MagicMock,
        mock_discover: MagicMock,
        mock_pid: MagicMock,
    ) -> None:
        status = get_status()
        assert status["okular_running"] is True
        assert status["open_pdfs"] == 1
        assert status["current_session"] is None

    @patch("okular_session.core.get_okular_pid", return_value=None)
    def test_okular_not_running(self, mock_pid: MagicMock) -> None:
        status = get_status()
        assert status["okular_running"] is False
        assert status["open_pdfs"] == 0

    @patch("okular_session.core.get_okular_pid", return_value="1234")
    @patch("okular_session.core.discover_open_pdfs", return_value=["a.pdf"])
    @patch("okular_session.core.list_sessions")
    @patch("okular_session.core.session_path")
    def test_matches_current_session(
        self,
        mock_path: MagicMock,
        mock_list: MagicMock,
        mock_discover: MagicMock,
        mock_pid: MagicMock,
    ) -> None:
        mock_list.return_value = [{"name": "work", "files": 1}]
        p = MagicMock(spec=Path)
        p.read_text.return_value = json.dumps({"files": ["a.pdf"]})
        mock_path.return_value = p
        status = get_status()
        assert status["current_session"] == "work"


# ---------------------------------------------------------------------------
# delete_session
# ---------------------------------------------------------------------------


class TestDeleteSession:
    @patch("okular_session.core.session_path")
    def test_delete_existing(self, mock_path: MagicMock) -> None:
        p = MagicMock(spec=Path)
        p.exists.return_value = True
        mock_path.return_value = p
        assert delete_session("work") is True
        p.unlink.assert_called_once()

    @patch("okular_session.core.session_path")
    def test_delete_missing(self, mock_path: MagicMock) -> None:
        p = MagicMock(spec=Path)
        p.exists.return_value = False
        mock_path.return_value = p
        assert delete_session("work") is False
        p.unlink.assert_not_called()


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------


class TestCli:
    def test_help_succeeds(self) -> None:
        from okular_session.cli import build_parser

        parser = build_parser()
        assert parser.prog == "okular-session"
        choices = parser._subparsers._group_actions[0].choices
        assert set(choices) == {
            "save",
            "restore",
            "list",
            "status",
            "delete",
            "watch",
            "launchd",
        }
