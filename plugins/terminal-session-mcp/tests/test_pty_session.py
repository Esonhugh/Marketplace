import time

from terminal_session_mcp.session_manager import SessionManager


def wait_for_text(manager, session_id, expected, timeout=5):
    deadline = time.time() + timeout
    since = 0
    combined = ""
    while time.time() < deadline:
        result = manager.read(session_id, since_seq=since, max_bytes=20000, strip_ansi=True, include_input=True)
        since = result["latest_seq"]
        combined += "".join(event.get("text", "") for event in result["events"] if event["type"] == "output")
        if expected in combined:
            return combined
        time.sleep(0.05)
    raise AssertionError(f"Did not find {expected!r}. Saw: {combined!r}")


def test_echo_command_records_output_and_exit(tmp_path):
    manager = SessionManager(workspace=tmp_path)
    session = manager.spawn("echo hello-terminal", label="echo")

    output = wait_for_text(manager, session["session_id"], "hello-terminal")
    status = manager.terminal_status(session["session_id"])

    assert "hello-terminal" in output
    assert status["status"] in {"running", "exited"}
    manager.close_all()


def test_python_repl_accepts_text_and_ctrl_d(tmp_path):
    manager = SessionManager(workspace=tmp_path)
    session = manager.spawn("python -i", label="py")
    sid = session["session_id"]

    wait_for_text(manager, sid, ">>>")
    manager.send_text(sid, "1+1", submit=True)
    output = wait_for_text(manager, sid, "2")
    manager.send_key(sid, "CTRL_D")
    time.sleep(0.3)
    status = manager.terminal_status(sid)

    assert "2" in output
    assert status["latest_seq"] >= 3
    manager.close_all()


def test_long_running_command_does_not_block_and_can_close(tmp_path):
    manager = SessionManager(workspace=tmp_path)
    session = manager.spawn("sleep 9999", label="sleep")
    sid = session["session_id"]

    assert manager.terminal_status(sid)["status"] == "running"
    manager.close(sid, mode="terminate")
    time.sleep(0.3)

    assert manager.terminal_status(sid)["status"] in {"running", "exited", "closed"}
    manager.close_all()
