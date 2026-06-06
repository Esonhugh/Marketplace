import json

import pytest

from terminal_session_mcp.models import SessionMetadata, STATUS_RUNNING
from terminal_session_mcp.storage import Storage


def metadata(session_id="term_test"):
    return SessionMetadata(
        version=1,
        session_id=session_id,
        label="test",
        command="echo hello",
        cwd="/tmp",
        env={},
        pid=123,
        cols=120,
        rows=40,
        status=STATUS_RUNNING,
        exit_code=None,
        created_at="2026-06-07T00:00:00.000Z",
    )


def test_create_session_writes_metadata_and_index(tmp_path):
    storage = Storage(tmp_path / ".terminal-debug")
    meta = metadata()

    storage.create_session(meta)

    session_dir = tmp_path / ".terminal-debug" / "sessions" / "term_test"
    assert (session_dir / "metadata.json").exists()
    assert (tmp_path / ".terminal-debug" / "index.json").exists()
    saved = json.loads((session_dir / "metadata.json").read_text())
    assert saved["session_id"] == "term_test"


def test_rejects_session_ids_that_escape_storage_root(tmp_path):
    storage = Storage(tmp_path / ".terminal-debug")

    with pytest.raises(ValueError, match="Invalid session_id"):
        storage.session_dir("../escape")

    with pytest.raises(ValueError, match="Invalid session_id"):
        storage.session_dir("term_bad/escape_abcdef")


def test_append_event_and_transcripts(tmp_path):
    storage = Storage(tmp_path / ".terminal-debug")
    meta = metadata()
    storage.create_session(meta)

    event = {"seq": 1, "ts": "now", "type": "output", "session_id": "term_test", "text": "\x1b[31mhello\x1b[0m"}
    storage.append_event("term_test", event)
    storage.append_transcript("term_test", event)

    session_dir = tmp_path / ".terminal-debug" / "sessions" / "term_test"
    events = (session_dir / "events.jsonl").read_text()
    assert "hello" in events
    assert "\x1b[31mhello" in (session_dir / "transcript.ansi").read_text()
    assert "hello" in (session_dir / "transcript.txt").read_text()
