from terminal_session_mcp.models import SessionMetadata, STATUS_RUNNING
from terminal_session_mcp.recorder import Recorder
from terminal_session_mcp.storage import Storage


def make_recorder(tmp_path):
    storage = Storage(tmp_path / ".terminal-debug")
    meta = SessionMetadata(
        version=1,
        session_id="term_test",
        label="test",
        command="python -i",
        cwd="/tmp",
        env={},
        pid=123,
        cols=120,
        rows=40,
        status=STATUS_RUNNING,
        exit_code=None,
        created_at="2026-06-07T00:00:00.000Z",
    )
    storage.create_session(meta)
    return Recorder(storage, meta), storage, meta


def test_recorder_assigns_sequences_and_persists(tmp_path):
    recorder, storage, _ = make_recorder(tmp_path)

    first = recorder.record_event("output", {"text": ">>> ", "bytes": 4})
    second = recorder.record_event("input_text", {"text": "1+1", "submit": True, "bytes": 4})

    assert first["seq"] == 1
    assert second["seq"] == 2
    events = storage.read_events_after("term_test", 0)
    assert [event["type"] for event in events] == ["output", "input_text"]


def test_read_events_filters_and_truncates(tmp_path):
    recorder, _, _ = make_recorder(tmp_path)
    recorder.record_event("output", {"text": "first", "bytes": 5})
    recorder.record_event("output", {"text": "second", "bytes": 6})

    result = recorder.read_events(since_seq=1, max_bytes=1000, include_input=False, strip_ansi=True)

    assert result["latest_seq"] == 2
    assert result["events"][0]["text"] == "second"
    assert result["truncated"] is False


def test_input_is_excluded_by_default(tmp_path):
    recorder, _, _ = make_recorder(tmp_path)
    recorder.record_event("input_text", {"text": "secret", "submit": True, "bytes": 7})
    recorder.record_event("output", {"text": "ok", "bytes": 2})

    result = recorder.read_events(since_seq=0, max_bytes=100, include_input=False, strip_ansi=True)

    assert [event["type"] for event in result["events"]] == ["output"]
