import time

from terminal_session_mcp.session_manager import SessionManager


def collect_output(manager, session_id, timeout=5):
    deadline = time.time() + timeout
    since = 0
    text = ""
    while time.time() < deadline:
        result = manager.read(session_id, since_seq=since, max_bytes=20000, strip_ansi=True, include_input=True)
        since = result["latest_seq"]
        text += "".join(event.get("text", "") for event in result["events"] if event["type"] == "output")
        time.sleep(0.05)
    return text


def test_multiple_sessions_do_not_mix_outputs(tmp_path):
    manager = SessionManager(workspace=tmp_path)
    py = manager.spawn("python -i", label="py")
    shell = manager.spawn("sh", label="shell")

    time.sleep(0.5)
    manager.send_text(py["session_id"], "10*10", submit=True)
    manager.send_text(shell["session_id"], "echo shell-ok", submit=True)

    py_output = collect_output(manager, py["session_id"])
    shell_output = collect_output(manager, shell["session_id"])

    assert "100" in py_output
    assert "shell-ok" in shell_output
    assert "shell-ok" not in py_output
    manager.close_all()


def test_list_and_export_transcript(tmp_path):
    manager = SessionManager(workspace=tmp_path)
    session = manager.spawn("echo export-ok", label="export")
    time.sleep(0.5)

    listed = manager.list(include_closed=True)
    exported = manager.export_transcript(session["session_id"], format="markdown")

    assert any(item["session_id"] == session["session_id"] for item in listed["sessions"])
    assert exported["path"].endswith("summary.md")
    assert exported["bytes"] > 0
    manager.close_all()
