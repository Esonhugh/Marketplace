from terminal_session_mcp.server import create_manager, health_check


def test_create_manager_uses_workspace_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMINAL_SESSION_WORKSPACE", str(tmp_path))
    manager = create_manager()
    assert manager.workspace == tmp_path.resolve()


def test_health_check_returns_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMINAL_SESSION_WORKSPACE", str(tmp_path))
    result = health_check()
    assert result["status"] == "ok"
    assert result["storage_root"].endswith(".terminal-debug")
