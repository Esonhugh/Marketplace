import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _project_version():
    for line in (ROOT / "pyproject.toml").read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("version ="):
            return stripped.split("=", 1)[1].strip().strip('"')
    raise AssertionError("project version not found in pyproject.toml")


def test_pyproject_declares_mcp_dependency():
    text = (ROOT / "pyproject.toml").read_text()
    assert 'name = "detective-plugin"' in text
    assert '"mcp' in text
    assert '"pytest' in text


def test_mcp_json_uses_uv_and_plugin_root():
    config = json.loads((ROOT / ".mcp.json").read_text())
    server = config["detective"]
    assert server["command"] == "uv"
    assert server["args"] == [
        "--directory",
        "${CLAUDE_PLUGIN_ROOT}",
        "run",
        "python",
        "-m",
        "detective_mcp.server",
    ]
    assert server["env"]["DETECTIVE_WORKSPACE"] == "${PWD}"


def test_package_imports():
    import detective_mcp

    assert detective_mcp.__version__ == _project_version()


def test_package_version_comes_from_project_metadata(monkeypatch):
    import importlib
    import importlib.metadata

    import detective_mcp

    def fake_version(name):
        assert name == "detective-plugin"
        return "9.9.9"

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    try:
        reloaded = importlib.reload(detective_mcp)
        assert reloaded.__version__ == "9.9.9"
    finally:
        monkeypatch.undo()
        importlib.reload(detective_mcp)
