# Terminal Session MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `terminal-session-mcp` marketplace plugin: a `uv`-launched stdio MCP server that manages concurrent PTY terminal sessions, sends text/keys, records full bidirectional transcripts, exports evidence, and is verified through Claude CLI.

**Architecture:** Create a focused Python package under `plugins/terminal-session-mcp/terminal_session_mcp/`. `server.py` exposes MCP tools, `SessionManager` owns live sessions, `PTYSession` wraps `pexpect`, `Recorder` writes event streams, and `Storage` persists `.terminal-debug` artifacts. The plugin also ships a Claude Code skill, slash command, plugin manifest, MCP config, docs, and tests.

**Tech Stack:** Python 3.11+, `uv`, `mcp>=1.0.0`, `pexpect>=4.9.0`, `pytest>=8.0.0`, stdio MCP, Unix PTY/macOS/Linux.

---

## Scope Check

The spec contains one coherent plugin with supporting docs and tests. It touches several subsystems, but they are all required to produce one testable marketplace plugin. Implement in dependency order: scaffold → pure utilities → storage/recorder → PTY/session manager → MCP tools → plugin docs → verification.

## File Structure

Create these files:

- `plugins/terminal-session-mcp/.claude-plugin/plugin.json` — Claude Code plugin metadata.
- `plugins/terminal-session-mcp/.mcp.json` — stdio MCP launch config using `uv`.
- `plugins/terminal-session-mcp/pyproject.toml` — Python package and test configuration.
- `plugins/terminal-session-mcp/terminal_session_mcp/__init__.py` — package version.
- `plugins/terminal-session-mcp/terminal_session_mcp/__main__.py` — module entrypoint.
- `plugins/terminal-session-mcp/terminal_session_mcp/timeutil.py` — UTC timestamp helper.
- `plugins/terminal-session-mcp/terminal_session_mcp/models.py` — dataclasses and status constants.
- `plugins/terminal-session-mcp/terminal_session_mcp/keymap.py` — key-name to byte mapping.
- `plugins/terminal-session-mcp/terminal_session_mcp/ansi.py` — ANSI stripping.
- `plugins/terminal-session-mcp/terminal_session_mcp/storage.py` — `.terminal-debug` filesystem persistence.
- `plugins/terminal-session-mcp/terminal_session_mcp/recorder.py` — event sequencing and transcript writing.
- `plugins/terminal-session-mcp/terminal_session_mcp/pty_session.py` — pexpect-backed PTY session.
- `plugins/terminal-session-mcp/terminal_session_mcp/session_manager.py` — active/historical session orchestration.
- `plugins/terminal-session-mcp/terminal_session_mcp/server.py` — MCP tools.
- `plugins/terminal-session-mcp/skills/terminal-session-debugging/SKILL.md` — triggering and workflow skill.
- `plugins/terminal-session-mcp/skills/terminal-session-debugging/README.md` — skill docs.
- `plugins/terminal-session-mcp/skills/terminal-session-debugging/README-zh.md` — Chinese skill docs.
- `plugins/terminal-session-mcp/commands/terminal-debug.md` — slash command prompt wrapper.
- `plugins/terminal-session-mcp/README.md` — plugin docs.
- `plugins/terminal-session-mcp/README-zh.md` — Chinese plugin docs.
- `plugins/terminal-session-mcp/tests/test_keymap.py` — keymap tests.
- `plugins/terminal-session-mcp/tests/test_ansi.py` — ANSI tests.
- `plugins/terminal-session-mcp/tests/test_storage.py` — storage tests.
- `plugins/terminal-session-mcp/tests/test_recorder.py` — recorder tests.
- `plugins/terminal-session-mcp/tests/test_pty_session.py` — PTY integration tests.
- `plugins/terminal-session-mcp/tests/test_session_manager.py` — session manager integration tests.
- `plugins/terminal-session-mcp/tests/test_server_tools.py` — MCP tool smoke tests.

Modify these files:

- `README.md` — add marketplace catalog row and plugin section.
- `README-zh.md` — add Chinese marketplace catalog row and plugin section.

---

### Task 1: Scaffold plugin package and manifests

**Files:**
- Create: `plugins/terminal-session-mcp/.claude-plugin/plugin.json`
- Create: `plugins/terminal-session-mcp/.mcp.json`
- Create: `plugins/terminal-session-mcp/pyproject.toml`
- Create: `plugins/terminal-session-mcp/terminal_session_mcp/__init__.py`
- Create: `plugins/terminal-session-mcp/terminal_session_mcp/__main__.py`
- Create: `plugins/terminal-session-mcp/terminal_session_mcp/server.py`

- [ ] **Step 1: Create plugin metadata**

Create `plugins/terminal-session-mcp/.claude-plugin/plugin.json`:

```json
{
  "name": "terminal-session-mcp",
  "version": "0.1.0",
  "description": "A stdio MCP server for simulated PTY terminal sessions with multi-session concurrency, key input, long-running command support, and full bidirectional transcript recording.",
  "author": {
    "name": "Esonhugh",
    "url": "https://github.com/esonhugh"
  },
  "license": "MIT",
  "keywords": [
    "terminal",
    "mcp",
    "pty",
    "cli",
    "debugging",
    "repl",
    "tui",
    "ssh",
    "telnet",
    "recorder"
  ]
}
```

- [ ] **Step 2: Create stdio MCP config**

Create `plugins/terminal-session-mcp/.mcp.json`:

```json
{
  "terminal-session": {
    "command": "uv",
    "args": [
      "--directory",
      "${CLAUDE_PLUGIN_ROOT}",
      "run",
      "python",
      "-m",
      "terminal_session_mcp"
    ],
    "env": {
      "TERMINAL_SESSION_WORKSPACE": "${PWD}"
    }
  }
}
```

- [ ] **Step 3: Create Python project config**

Create `plugins/terminal-session-mcp/pyproject.toml`:

```toml
[project]
name = "terminal-session-mcp"
version = "0.1.0"
description = "PTY terminal session recorder MCP server for Claude Code"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "pexpect>=4.9.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 4: Create package entry files**

Create `plugins/terminal-session-mcp/terminal_session_mcp/__init__.py`:

```python
"""PTY terminal session MCP server for Claude Code."""

__version__ = "0.1.0"
```

Create `plugins/terminal-session-mcp/terminal_session_mcp/__main__.py`:

```python
from terminal_session_mcp.server import main

if __name__ == "__main__":
    main()
```

Create temporary `plugins/terminal-session-mcp/terminal_session_mcp/server.py`:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("terminal-session")


@mcp.tool()
def health_check() -> dict:
    return {"status": "ok", "implementation": "scaffold"}


def main() -> None:
    mcp.run()
```

- [ ] **Step 5: Verify package starts**

Run:

```bash
cd plugins/terminal-session-mcp && uv run python -m terminal_session_mcp
```

Expected: command starts and waits for MCP stdio input. Stop it with Ctrl-C. No ordinary stdout log should appear before MCP input.

- [ ] **Step 6: Commit scaffold**

```bash
git add plugins/terminal-session-mcp/.claude-plugin/plugin.json \
  plugins/terminal-session-mcp/.mcp.json \
  plugins/terminal-session-mcp/pyproject.toml \
  plugins/terminal-session-mcp/terminal_session_mcp/__init__.py \
  plugins/terminal-session-mcp/terminal_session_mcp/__main__.py \
  plugins/terminal-session-mcp/terminal_session_mcp/server.py
git commit -m "feat: scaffold terminal session MCP plugin"
```

---

### Task 2: Implement pure utility modules with tests

**Files:**
- Create: `plugins/terminal-session-mcp/terminal_session_mcp/timeutil.py`
- Create: `plugins/terminal-session-mcp/terminal_session_mcp/models.py`
- Create: `plugins/terminal-session-mcp/terminal_session_mcp/keymap.py`
- Create: `plugins/terminal-session-mcp/terminal_session_mcp/ansi.py`
- Test: `plugins/terminal-session-mcp/tests/test_keymap.py`
- Test: `plugins/terminal-session-mcp/tests/test_ansi.py`

- [ ] **Step 1: Write keymap tests**

Create `plugins/terminal-session-mcp/tests/test_keymap.py`:

```python
import pytest

from terminal_session_mcp.keymap import key_to_bytes, supported_keys


def test_basic_keys_map_to_terminal_bytes():
    assert key_to_bytes("ENTER") == b"\r"
    assert key_to_bytes("TAB") == b"\t"
    assert key_to_bytes("ESC") == b"\x1b"
    assert key_to_bytes("CTRL_C") == b"\x03"
    assert key_to_bytes("CTRL_D") == b"\x04"
    assert key_to_bytes("UP") == b"\x1b[A"
    assert key_to_bytes("DOWN") == b"\x1b[B"
    assert key_to_bytes("RIGHT") == b"\x1b[C"
    assert key_to_bytes("LEFT") == b"\x1b[D"


def test_ctrl_letters_are_generated():
    assert key_to_bytes("CTRL_A") == b"\x01"
    assert key_to_bytes("CTRL_Z") == b"\x1a"


def test_supported_keys_include_common_controls():
    keys = supported_keys()
    assert "ENTER" in keys
    assert "CTRL_C" in keys
    assert "F12" in keys


def test_invalid_key_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported key"):
        key_to_bytes("CTRL_ALT_DELETE")
```

- [ ] **Step 2: Run keymap tests and verify failure**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest tests/test_keymap.py -v
```

Expected: FAIL because `terminal_session_mcp.keymap` does not exist.

- [ ] **Step 3: Implement keymap**

Create `plugins/terminal-session-mcp/terminal_session_mcp/keymap.py`:

```python
from __future__ import annotations

_BASE_KEYMAP: dict[str, bytes] = {
    "ENTER": b"\r",
    "TAB": b"\t",
    "ESC": b"\x1b",
    "BACKSPACE": b"\x7f",
    "DELETE": b"\x1b[3~",
    "UP": b"\x1b[A",
    "DOWN": b"\x1b[B",
    "RIGHT": b"\x1b[C",
    "LEFT": b"\x1b[D",
    "HOME": b"\x1b[H",
    "END": b"\x1b[F",
    "PAGE_UP": b"\x1b[5~",
    "PAGE_DOWN": b"\x1b[6~",
    "F1": b"\x1bOP",
    "F2": b"\x1bOQ",
    "F3": b"\x1bOR",
    "F4": b"\x1bOS",
    "F5": b"\x1b[15~",
    "F6": b"\x1b[17~",
    "F7": b"\x1b[18~",
    "F8": b"\x1b[19~",
    "F9": b"\x1b[20~",
    "F10": b"\x1b[21~",
    "F11": b"\x1b[23~",
    "F12": b"\x1b[24~",
}


def _build_keymap() -> dict[str, bytes]:
    keys = dict(_BASE_KEYMAP)
    for codepoint in range(ord("A"), ord("Z") + 1):
        letter = chr(codepoint)
        keys[f"CTRL_{letter}"] = bytes([codepoint - ord("A") + 1])
    return keys


_KEYMAP = _build_keymap()


def supported_keys() -> list[str]:
    return sorted(_KEYMAP)


def key_to_bytes(key: str) -> bytes:
    normalized = key.strip().upper()
    try:
        return _KEYMAP[normalized]
    except KeyError as exc:
        sample = ", ".join(supported_keys()[:12])
        raise ValueError(f"Unsupported key: {key}. Examples: {sample}") from exc
```

- [ ] **Step 4: Write ANSI tests**

Create `plugins/terminal-session-mcp/tests/test_ansi.py`:

```python
from terminal_session_mcp.ansi import strip_ansi


def test_strip_color_sequences():
    assert strip_ansi("\x1b[31mred\x1b[0m") == "red"


def test_strip_cursor_sequences():
    assert strip_ansi("hello\x1b[2K\rworld") == "hello\rworld"


def test_plain_text_is_unchanged():
    assert strip_ansi("plain text") == "plain text"
```

- [ ] **Step 5: Run ANSI tests and verify failure**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest tests/test_ansi.py -v
```

Expected: FAIL because `terminal_session_mcp.ansi` does not exist.

- [ ] **Step 6: Implement time, models, and ANSI utilities**

Create `plugins/terminal-session-mcp/terminal_session_mcp/timeutil.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
```

Create `plugins/terminal-session-mcp/terminal_session_mcp/models.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

STATUS_STARTING = "starting"
STATUS_RUNNING = "running"
STATUS_EXITED = "exited"
STATUS_CLOSED = "closed"
STATUS_FAILED = "failed"
STATUS_ORPHANED = "orphaned"

ACTIVE_STATUSES = {STATUS_STARTING, STATUS_RUNNING}


@dataclass
class TerminalEvent:
    seq: int
    ts: str
    type: str
    session_id: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "seq": self.seq,
            "ts": self.ts,
            "type": self.type,
            "session_id": self.session_id,
        }
        data.update(self.payload)
        return data


@dataclass
class SessionMetadata:
    version: int
    session_id: str
    label: str | None
    command: str
    cwd: str
    env: dict[str, str]
    pid: int | None
    cols: int
    rows: int
    status: str
    exit_code: int | None
    created_at: str
    ended_at: str | None = None
    latest_seq: int = 0
    last_output_at: str | None = None
    output_bytes: int = 0
    event_count: int = 0
    reader_status: str = "starting"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

Create `plugins/terminal-session-mcp/terminal_session_mcp/ansi.py`:

```python
from __future__ import annotations

import re

ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)
```

- [ ] **Step 7: Run utility tests and verify pass**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest tests/test_keymap.py tests/test_ansi.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit utilities**

```bash
git add plugins/terminal-session-mcp/terminal_session_mcp/timeutil.py \
  plugins/terminal-session-mcp/terminal_session_mcp/models.py \
  plugins/terminal-session-mcp/terminal_session_mcp/keymap.py \
  plugins/terminal-session-mcp/terminal_session_mcp/ansi.py \
  plugins/terminal-session-mcp/tests/test_keymap.py \
  plugins/terminal-session-mcp/tests/test_ansi.py
git commit -m "feat: add terminal session utility modules"
```

---

### Task 3: Implement storage and recorder

**Files:**
- Create: `plugins/terminal-session-mcp/terminal_session_mcp/storage.py`
- Create: `plugins/terminal-session-mcp/terminal_session_mcp/recorder.py`
- Test: `plugins/terminal-session-mcp/tests/test_storage.py`
- Test: `plugins/terminal-session-mcp/tests/test_recorder.py`

- [ ] **Step 1: Write storage tests**

Create `plugins/terminal-session-mcp/tests/test_storage.py`:

```python
import json

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


def test_append_event_and_transcripts(tmp_path):
    storage = Storage(tmp_path / ".terminal-debug")
    meta = metadata()
    storage.create_session(meta)

    event = {"seq": 1, "ts": "now", "type": "output", "session_id": "term_test", "text": "\x1b[31mhello\x1b[0m"}
    storage.append_event("term_test", event)
    storage.append_transcript("term_test", event)

    events = (tmp_path / ".terminal-debug" / "sessions" / "term_test" / "events.jsonl").read_text()
    assert "hello" in events
    assert "\x1b[31mhello" in (tmp_path / ".terminal-debug" / "sessions" / "term_test" / "transcript.ansi").read_text()
    assert "hello" in (tmp_path / ".terminal-debug" / "sessions" / "term_test" / "transcript.txt").read_text()
```

- [ ] **Step 2: Run storage tests and verify failure**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest tests/test_storage.py -v
```

Expected: FAIL because `storage.py` does not exist.

- [ ] **Step 3: Implement storage**

Create `plugins/terminal-session-mcp/terminal_session_mcp/storage.py`:

```python
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from terminal_session_mcp.ansi import strip_ansi
from terminal_session_mcp.models import SessionMetadata
from terminal_session_mcp.timeutil import utc_now_iso


class Storage:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.sessions_root = self.root / "sessions"
        self.root.mkdir(parents=True, exist_ok=True)
        self.sessions_root.mkdir(parents=True, exist_ok=True)

    def session_dir(self, session_id: str) -> Path:
        return self.sessions_root / session_id

    def create_session(self, metadata: SessionMetadata) -> None:
        path = self.session_dir(metadata.session_id)
        path.mkdir(parents=True, exist_ok=False)
        (path / "events.jsonl").touch()
        (path / "transcript.ansi").touch()
        (path / "transcript.txt").touch()
        self.write_metadata(metadata)
        self.update_index(metadata)

    def write_metadata(self, metadata: SessionMetadata) -> None:
        path = self.session_dir(metadata.session_id) / "metadata.json"
        self._atomic_write_json(path, metadata.to_dict())

    def read_metadata(self, session_id: str) -> dict[str, Any]:
        path = self.session_dir(session_id) / "metadata.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def append_event(self, session_id: str, event: dict[str, Any]) -> None:
        path = self.session_dir(session_id) / "events.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def append_transcript(self, session_id: str, event: dict[str, Any]) -> None:
        ansi_line = self._event_to_transcript_line(event, strip=False)
        text_line = self._event_to_transcript_line(event, strip=True)
        if ansi_line:
            with (self.session_dir(session_id) / "transcript.ansi").open("a", encoding="utf-8") as handle:
                handle.write(ansi_line)
        if text_line:
            with (self.session_dir(session_id) / "transcript.txt").open("a", encoding="utf-8") as handle:
                handle.write(text_line)

    def read_events_after(self, session_id: str, since_seq: int) -> list[dict[str, Any]]:
        path = self.session_dir(session_id) / "events.jsonl"
        events: list[dict[str, Any]] = []
        if not path.exists():
            return events
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if int(event["seq"]) > since_seq:
                events.append(event)
        return events

    def update_index(self, metadata: SessionMetadata) -> None:
        index_path = self.root / "index.json"
        if index_path.exists():
            index = json.loads(index_path.read_text(encoding="utf-8"))
        else:
            index = {"version": 1, "updated_at": utc_now_iso(), "sessions": []}
        entry = {
            "session_id": metadata.session_id,
            "label": metadata.label,
            "command": metadata.command,
            "status": metadata.status,
            "created_at": metadata.created_at,
            "ended_at": metadata.ended_at,
            "path": f"sessions/{metadata.session_id}",
        }
        sessions = [s for s in index.get("sessions", []) if s.get("session_id") != metadata.session_id]
        sessions.append(entry)
        index["sessions"] = sessions
        index["updated_at"] = utc_now_iso()
        self._atomic_write_json(index_path, index)

    def list_index(self) -> list[dict[str, Any]]:
        index_path = self.root / "index.json"
        if not index_path.exists():
            return []
        return json.loads(index_path.read_text(encoding="utf-8")).get("sessions", [])

    def export_markdown(self, session_id: str) -> Path:
        meta = self.read_metadata(session_id)
        transcript_path = self.session_dir(session_id) / "transcript.txt"
        transcript = transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
        summary = self.session_dir(session_id) / "summary.md"
        summary.write_text(
            "\n".join(
                [
                    f"# Terminal Session: {meta.get('label') or session_id}",
                    "",
                    f"- Session: `{session_id}`",
                    f"- Command: `{meta.get('command')}`",
                    f"- CWD: `{meta.get('cwd')}`",
                    f"- Status: `{meta.get('status')}`",
                    f"- Exit code: `{meta.get('exit_code')}`",
                    f"- Started: `{meta.get('created_at')}`",
                    f"- Ended: `{meta.get('ended_at')}`",
                    "",
                    "## Transcript",
                    "",
                    "```text",
                    transcript,
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return summary

    def _event_to_transcript_line(self, event: dict[str, Any], strip: bool) -> str:
        event_type = event.get("type")
        if event_type == "output":
            text = event.get("text", "")
            return strip_ansi(text) if strip else text
        if event_type == "input_text":
            suffix = " [submit]" if event.get("submit") else ""
            return f"\n[INPUT_TEXT{suffix}] {event.get('text', '')}\n"
        if event_type == "input_key":
            return f"\n[INPUT_KEY] {event.get('key')}\n"
        if event_type == "resize":
            return f"\n[RESIZE] {event.get('cols')}x{event.get('rows')}\n"
        if event_type == "close":
            return f"\n[CLOSE] {event.get('mode')}\n"
        if event_type == "exit":
            return f"\n[EXIT] code={event.get('exit_code')} signal={event.get('signal')}\n"
        if event_type == "error":
            return f"\n[ERROR] {event.get('message')}\n"
        return ""

    def _atomic_write_json(self, path: Path, data: dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
```

- [ ] **Step 4: Run storage tests and verify pass**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest tests/test_storage.py -v
```

Expected: PASS.

- [ ] **Step 5: Write recorder tests**

Create `plugins/terminal-session-mcp/tests/test_recorder.py`:

```python
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

    result = recorder.read_events(since_seq=1, max_bytes=100, include_input=False, strip_ansi=True)

    assert result["latest_seq"] == 2
    assert result["events"][0]["text"] == "second"
    assert result["truncated"] is False


def test_input_is_excluded_by_default(tmp_path):
    recorder, _, _ = make_recorder(tmp_path)
    recorder.record_event("input_text", {"text": "secret", "submit": True, "bytes": 7})
    recorder.record_event("output", {"text": "ok", "bytes": 2})

    result = recorder.read_events(since_seq=0, max_bytes=100, include_input=False, strip_ansi=True)

    assert [event["type"] for event in result["events"]] == ["output"]
```

- [ ] **Step 6: Run recorder tests and verify failure**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest tests/test_recorder.py -v
```

Expected: FAIL because `recorder.py` does not exist.

- [ ] **Step 7: Implement recorder**

Create `plugins/terminal-session-mcp/terminal_session_mcp/recorder.py`:

```python
from __future__ import annotations

import threading
from collections import deque
from typing import Any

from terminal_session_mcp.ansi import strip_ansi
from terminal_session_mcp.models import SessionMetadata, TerminalEvent
from terminal_session_mcp.storage import Storage
from terminal_session_mcp.timeutil import utc_now_iso

_INPUT_EVENT_TYPES = {"input_text", "input_key", "resize", "close"}


class Recorder:
    def __init__(self, storage: Storage, metadata: SessionMetadata, memory_events: int = 1000):
        self.storage = storage
        self.metadata = metadata
        self._events: deque[dict[str, Any]] = deque(maxlen=memory_events)
        self._seq = metadata.latest_seq
        self._lock = threading.Lock()

    @property
    def latest_seq(self) -> int:
        return self._seq

    def record_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._seq += 1
            event = TerminalEvent(
                seq=self._seq,
                ts=utc_now_iso(),
                type=event_type,
                session_id=self.metadata.session_id,
                payload=payload,
            ).to_dict()
            self._events.append(event)
            self._update_metadata_for_event(event)
            self.storage.append_event(self.metadata.session_id, event)
            self.storage.append_transcript(self.metadata.session_id, event)
            self.storage.write_metadata(self.metadata)
            self.storage.update_index(self.metadata)
            return event

    def read_events(self, since_seq: int, max_bytes: int, include_input: bool, strip_ansi: bool) -> dict[str, Any]:
        with self._lock:
            if self._events and since_seq >= self._events[0]["seq"] - 1:
                candidates = [event for event in self._events if event["seq"] > since_seq]
            else:
                candidates = self.storage.read_events_after(self.metadata.session_id, since_seq)

        returned: list[dict[str, Any]] = []
        total_bytes = 0
        truncated = False
        latest_seq = since_seq
        for event in candidates:
            if not include_input and event.get("type") in _INPUT_EVENT_TYPES:
                latest_seq = event["seq"]
                continue
            prepared = dict(event)
            if strip_ansi and prepared.get("type") == "output" and "text" in prepared:
                prepared["text"] = strip_ansi(prepared["text"])
            size = len(str(prepared).encode("utf-8"))
            if returned and total_bytes + size > max_bytes:
                truncated = True
                break
            if not returned and size > max_bytes:
                truncated = True
                if "text" in prepared:
                    encoded = prepared["text"].encode("utf-8")[:max_bytes]
                    prepared["text"] = encoded.decode("utf-8", errors="replace")
                returned.append(prepared)
                latest_seq = prepared["seq"]
                break
            returned.append(prepared)
            total_bytes += size
            latest_seq = prepared["seq"]
        return {
            "events": returned,
            "latest_seq": latest_seq,
            "session_latest_seq": self._seq,
            "truncated": truncated,
        }

    def _update_metadata_for_event(self, event: dict[str, Any]) -> None:
        self.metadata.latest_seq = event["seq"]
        self.metadata.event_count += 1
        event_type = event.get("type")
        if event_type == "output":
            byte_count = int(event.get("bytes", len(event.get("text", "").encode("utf-8"))))
            self.metadata.output_bytes += byte_count
            self.metadata.last_output_at = event["ts"]
        elif event_type == "exit":
            self.metadata.status = "exited"
            self.metadata.exit_code = event.get("exit_code")
            self.metadata.ended_at = event["ts"]
            self.metadata.reader_status = "stopped"
        elif event_type == "error":
            self.metadata.reader_status = "error"
```

- [ ] **Step 8: Run storage and recorder tests**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest tests/test_storage.py tests/test_recorder.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit storage and recorder**

```bash
git add plugins/terminal-session-mcp/terminal_session_mcp/storage.py \
  plugins/terminal-session-mcp/terminal_session_mcp/recorder.py \
  plugins/terminal-session-mcp/tests/test_storage.py \
  plugins/terminal-session-mcp/tests/test_recorder.py
git commit -m "feat: record terminal session events"
```

---

### Task 4: Implement PTYSession and SessionManager

**Files:**
- Create: `plugins/terminal-session-mcp/terminal_session_mcp/pty_session.py`
- Create: `plugins/terminal-session-mcp/terminal_session_mcp/session_manager.py`
- Test: `plugins/terminal-session-mcp/tests/test_pty_session.py`
- Test: `plugins/terminal-session-mcp/tests/test_session_manager.py`

- [ ] **Step 1: Write PTY integration tests**

Create `plugins/terminal-session-mcp/tests/test_pty_session.py`:

```python
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
```

- [ ] **Step 2: Run PTY tests and verify failure**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest tests/test_pty_session.py -v
```

Expected: FAIL because `session_manager.py` and `pty_session.py` do not exist.

- [ ] **Step 3: Implement PTYSession**

Create `plugins/terminal-session-mcp/terminal_session_mcp/pty_session.py`:

```python
from __future__ import annotations

import signal
import threading
import time
from pathlib import Path
from typing import Any

import pexpect

from terminal_session_mcp.keymap import key_to_bytes
from terminal_session_mcp.models import STATUS_CLOSED, STATUS_FAILED, STATUS_RUNNING, SessionMetadata
from terminal_session_mcp.recorder import Recorder


class PTYSession:
    def __init__(self, metadata: SessionMetadata, recorder: Recorder):
        self.metadata = metadata
        self.recorder = recorder
        self.child: pexpect.spawn | None = None
        self._reader: threading.Thread | None = None
        self._lock = threading.RLock()
        self._stop_reader = threading.Event()

    def spawn(self) -> None:
        env = dict(self.metadata.env)
        self.child = pexpect.spawn(
            "/bin/sh",
            ["-lc", self.metadata.command],
            cwd=self.metadata.cwd,
            env=env or None,
            dimensions=(self.metadata.rows, self.metadata.cols),
            encoding=None,
            timeout=0,
        )
        self.metadata.pid = self.child.pid
        self.metadata.status = STATUS_RUNNING
        self.metadata.reader_status = "running"
        self.recorder.record_event(
            "spawn",
            {
                "command": self.metadata.command,
                "cwd": self.metadata.cwd,
                "pid": self.metadata.pid,
                "cols": self.metadata.cols,
                "rows": self.metadata.rows,
                "label": self.metadata.label,
            },
        )
        self._reader = threading.Thread(target=self._reader_loop, name=f"terminal-reader-{self.metadata.session_id}", daemon=True)
        self._reader.start()

    def send_text(self, text: str, submit: bool = False) -> dict[str, Any]:
        payload = text.encode("utf-8") + (b"\r" if submit else b"")
        written = self._write(payload)
        event = self.recorder.record_event("input_text", {"text": text, "submit": submit, "bytes": written})
        return {"session_id": self.metadata.session_id, "bytes_written": written, "recorded_seq": event["seq"]}

    def send_key(self, key: str) -> dict[str, Any]:
        payload = key_to_bytes(key)
        written = self._write(payload)
        event = self.recorder.record_event("input_key", {"key": key.strip().upper(), "bytes": written})
        return {"session_id": self.metadata.session_id, "key": key.strip().upper(), "bytes_written": written, "recorded_seq": event["seq"]}

    def resize(self, cols: int, rows: int) -> dict[str, Any]:
        if cols <= 0 or rows <= 0:
            raise ValueError("cols and rows must be positive")
        with self._lock:
            self._require_child()
            assert self.child is not None
            self.child.setwinsize(rows, cols)
            self.metadata.cols = cols
            self.metadata.rows = rows
        event = self.recorder.record_event("resize", {"cols": cols, "rows": rows})
        return {"session_id": self.metadata.session_id, "cols": cols, "rows": rows, "recorded_seq": event["seq"]}

    def status(self) -> dict[str, Any]:
        self._refresh_exit_status()
        meta = self.metadata.to_dict()
        meta["storage_path"] = str(Path(".terminal-debug") / "sessions" / self.metadata.session_id)
        return meta

    def close(self, mode: str) -> dict[str, Any]:
        normalized = mode.strip().lower()
        if normalized not in {"interrupt", "eof", "terminate", "kill"}:
            raise ValueError("mode must be one of interrupt, eof, terminate, kill")
        event = self.recorder.record_event("close", {"mode": normalized})
        with self._lock:
            if self.child is None or not self.child.isalive():
                self.metadata.status = "exited"
                return {"session_id": self.metadata.session_id, "mode": normalized, "status": self.metadata.status, "recorded_seq": event["seq"]}
            if normalized == "interrupt":
                self.child.sendcontrol("c")
            elif normalized == "eof":
                self.child.sendeof()
            elif normalized == "terminate":
                self.child.terminate(force=False)
            elif normalized == "kill":
                self.child.kill(signal.SIGKILL)
        return {"session_id": self.metadata.session_id, "mode": normalized, "status": "closing", "recorded_seq": event["seq"]}

    def close_forcefully(self) -> None:
        try:
            self.close("terminate")
            time.sleep(0.1)
            if self.child is not None and self.child.isalive():
                self.close("kill")
        except Exception:
            pass

    def _write(self, payload: bytes) -> int:
        with self._lock:
            self._require_child()
            assert self.child is not None
            if not self.child.isalive():
                raise RuntimeError(f"Session {self.metadata.session_id} is not running")
            self.child.write(payload)
            return len(payload)

    def _reader_loop(self) -> None:
        assert self.child is not None
        while not self._stop_reader.is_set():
            try:
                chunk = self.child.read_nonblocking(size=4096, timeout=0.1)
            except pexpect.TIMEOUT:
                self._refresh_exit_status()
                if self.metadata.status != STATUS_RUNNING:
                    break
                continue
            except pexpect.EOF:
                self._record_exit_once()
                break
            except OSError as exc:
                self.recorder.record_event("error", {"message": f"read failed: {exc}", "recoverable": True})
                self._record_exit_once()
                break
            if chunk:
                text = chunk.decode("utf-8", errors="replace")
                self.recorder.record_event("output", {"stream": "pty", "text": text, "bytes": len(chunk)})
        self.metadata.reader_status = "stopped"

    def _refresh_exit_status(self) -> None:
        with self._lock:
            if self.child is None:
                return
            if self.metadata.status == STATUS_RUNNING and not self.child.isalive():
                self._record_exit_once()

    def _record_exit_once(self) -> None:
        with self._lock:
            if self.child is None:
                return
            if self.metadata.status not in {STATUS_RUNNING, STATUS_FAILED, STATUS_CLOSED}:
                return
            exit_code = self.child.exitstatus
            signal_status = self.child.signalstatus
            self.recorder.record_event("exit", {"exit_code": exit_code, "signal": signal_status})

    def _require_child(self) -> None:
        if self.child is None:
            raise RuntimeError(f"Session {self.metadata.session_id} has not been spawned")
```

- [ ] **Step 4: Implement SessionManager**

Create `plugins/terminal-session-mcp/terminal_session_mcp/session_manager.py`:

```python
from __future__ import annotations

import os
import secrets
import threading
from pathlib import Path
from typing import Any

from terminal_session_mcp.models import STATUS_ORPHANED, STATUS_RUNNING, SessionMetadata
from terminal_session_mcp.pty_session import PTYSession
from terminal_session_mcp.recorder import Recorder
from terminal_session_mcp.storage import Storage
from terminal_session_mcp.timeutil import utc_now_iso


class SessionManager:
    def __init__(self, workspace: str | Path, max_active_sessions: int | None = None):
        self.workspace = Path(workspace).resolve()
        self.storage = Storage(self.workspace / ".terminal-debug")
        self.max_active_sessions = max_active_sessions or int(os.environ.get("TERMINAL_SESSION_MAX_ACTIVE", "16"))
        self._sessions: dict[str, PTYSession] = {}
        self._lock = threading.RLock()
        self._mark_orphaned_sessions()

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "workspace": str(self.workspace),
            "storage_root": str(self.storage.root),
            "active_sessions": len(self._sessions),
            "max_active_sessions": self.max_active_sessions,
            "platform": os.uname().sysname.lower() if hasattr(os, "uname") else os.name,
            "pty_backend": "pexpect",
        }

    def spawn(self, command: str, cwd: str | None = None, env: dict[str, str] | None = None, cols: int = 120, rows: int = 40, label: str | None = None) -> dict[str, Any]:
        if not command.strip():
            raise ValueError("command must not be empty")
        cwd_path = (self.workspace / cwd).resolve() if cwd else self.workspace
        if not cwd_path.exists():
            raise FileNotFoundError(f"Working directory does not exist: {cwd_path}")
        if cols <= 0 or rows <= 0:
            raise ValueError("cols and rows must be positive")
        with self._lock:
            self._prune_exited_sessions()
            if len(self._sessions) >= self.max_active_sessions:
                raise RuntimeError(f"Maximum active terminal sessions reached: {self.max_active_sessions}")
            session_id = self._new_session_id()
            metadata = SessionMetadata(
                version=1,
                session_id=session_id,
                label=label,
                command=command,
                cwd=str(cwd_path),
                env=env or {},
                pid=None,
                cols=cols,
                rows=rows,
                status="starting",
                exit_code=None,
                created_at=utc_now_iso(),
            )
            self.storage.create_session(metadata)
            recorder = Recorder(self.storage, metadata)
            session = PTYSession(metadata, recorder)
            session.spawn()
            self._sessions[session_id] = session
            return {
                "session_id": session_id,
                "label": label,
                "pid": metadata.pid,
                "status": metadata.status,
                "cwd": metadata.cwd,
                "cols": metadata.cols,
                "rows": metadata.rows,
                "created_at": metadata.created_at,
            }

    def read(self, session_id: str, since_seq: int = 0, max_bytes: int = 20000, strip_ansi: bool = True, include_input: bool = False) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is not None:
            result = session.recorder.read_events(since_seq, max_bytes, include_input, strip_ansi)
            result["session_id"] = session_id
            result["status"] = session.metadata.status
            return result
        metadata = self.storage.read_metadata(session_id)
        events = self.storage.read_events_after(session_id, since_seq)
        returned: list[dict[str, Any]] = []
        total = 0
        latest = since_seq
        truncated = False
        input_types = {"input_text", "input_key", "resize", "close"}
        for event in events:
            if not include_input and event.get("type") in input_types:
                latest = event["seq"]
                continue
            size = len(str(event).encode("utf-8"))
            if returned and total + size > max_bytes:
                truncated = True
                break
            returned.append(event)
            total += size
            latest = event["seq"]
        return {
            "session_id": session_id,
            "events": returned,
            "latest_seq": latest,
            "session_latest_seq": metadata.get("latest_seq", latest),
            "truncated": truncated,
            "status": metadata.get("status"),
        }

    def send_text(self, session_id: str, text: str, submit: bool = False) -> dict[str, Any]:
        return self._require_live(session_id).send_text(text, submit)

    def send_key(self, session_id: str, key: str) -> dict[str, Any]:
        return self._require_live(session_id).send_key(key)

    def resize(self, session_id: str, cols: int, rows: int) -> dict[str, Any]:
        return self._require_live(session_id).resize(cols, rows)

    def terminal_status(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is not None:
            return session.status()
        return self.storage.read_metadata(session_id)

    def close(self, session_id: str, mode: str = "terminate") -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            metadata = self.storage.read_metadata(session_id)
            return {"session_id": session_id, "status": metadata.get("status"), "message": "Session is not active"}
        return session.close(mode)

    def close_all(self) -> None:
        for session in list(self._sessions.values()):
            session.close_forcefully()

    def list(self, include_closed: bool = True) -> dict[str, Any]:
        active = {sid: session.status() for sid, session in self._sessions.items()}
        if not include_closed:
            return {"sessions": list(active.values())}
        historical = []
        for entry in self.storage.list_index():
            if entry["session_id"] not in active:
                historical.append(entry)
        return {"sessions": list(active.values()) + historical}

    def export_transcript(self, session_id: str, format: str = "markdown") -> dict[str, Any]:
        normalized = format.lower()
        session_dir = self.storage.session_dir(session_id)
        if normalized == "markdown":
            path = self.storage.export_markdown(session_id)
        elif normalized == "jsonl":
            path = session_dir / "events.jsonl"
        elif normalized == "text":
            path = session_dir / "transcript.txt"
        elif normalized == "ansi":
            path = session_dir / "transcript.ansi"
        else:
            raise ValueError("format must be one of jsonl, text, ansi, markdown")
        return {"session_id": session_id, "format": normalized, "path": str(path), "bytes": path.stat().st_size}

    def _require_live(self, session_id: str) -> PTYSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"No active terminal session found: {session_id}")
        if session.metadata.status != STATUS_RUNNING:
            raise RuntimeError(f"Session {session_id} is not running")
        return session

    def _new_session_id(self) -> str:
        stamp = utc_now_iso().replace("-", "").replace(":", "").replace(".", "").replace("Z", "")[:15]
        return f"term_{stamp}_{secrets.token_hex(3)}"

    def _prune_exited_sessions(self) -> None:
        for sid, session in list(self._sessions.items()):
            status = session.status()["status"]
            if status not in {"starting", STATUS_RUNNING}:
                self._sessions.pop(sid, None)

    def _mark_orphaned_sessions(self) -> None:
        for entry in self.storage.list_index():
            if entry.get("status") == STATUS_RUNNING:
                try:
                    data = self.storage.read_metadata(entry["session_id"])
                    data["status"] = STATUS_ORPHANED
                    data["ended_at"] = utc_now_iso()
                    meta = SessionMetadata(**data)
                    self.storage.write_metadata(meta)
                    self.storage.update_index(meta)
                except Exception:
                    continue
```

- [ ] **Step 5: Run PTY tests and fix any deterministic timing issue**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest tests/test_pty_session.py -v
```

Expected: PASS on macOS/Linux. If prompt timing is flaky, increase `wait_for_text` timeout to 10 seconds in the test file.

- [ ] **Step 6: Write session manager multi-session tests**

Create `plugins/terminal-session-mcp/tests/test_session_manager.py`:

```python
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
```

- [ ] **Step 7: Run PTY/session tests**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest tests/test_pty_session.py tests/test_session_manager.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit PTY session implementation**

```bash
git add plugins/terminal-session-mcp/terminal_session_mcp/pty_session.py \
  plugins/terminal-session-mcp/terminal_session_mcp/session_manager.py \
  plugins/terminal-session-mcp/tests/test_pty_session.py \
  plugins/terminal-session-mcp/tests/test_session_manager.py
git commit -m "feat: manage PTY terminal sessions"
```

---

### Task 5: Implement MCP server tools

**Files:**
- Modify: `plugins/terminal-session-mcp/terminal_session_mcp/server.py`
- Test: `plugins/terminal-session-mcp/tests/test_server_tools.py`

- [ ] **Step 1: Write server tool smoke tests**

Create `plugins/terminal-session-mcp/tests/test_server_tools.py`:

```python
import os

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
```

- [ ] **Step 2: Run server tests and verify failure against scaffold**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest tests/test_server_tools.py -v
```

Expected: FAIL because scaffold `server.py` does not expose `create_manager`.

- [ ] **Step 3: Replace server implementation with real tools**

Replace `plugins/terminal-session-mcp/terminal_session_mcp/server.py` with:

```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from terminal_session_mcp.session_manager import SessionManager

mcp = FastMCP("terminal-session")
_MANAGER: SessionManager | None = None


def create_manager() -> SessionManager:
    workspace = Path(os.environ.get("TERMINAL_SESSION_WORKSPACE", os.getcwd()))
    return SessionManager(workspace=workspace)


def get_manager() -> SessionManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = create_manager()
    return _MANAGER


@mcp.tool()
def health_check() -> dict[str, Any]:
    return get_manager().health_check()


@mcp.tool()
def spawn_terminal(
    command: str,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    cols: int = 120,
    rows: int = 40,
    label: str | None = None,
) -> dict[str, Any]:
    return get_manager().spawn(command=command, cwd=cwd, env=env, cols=cols, rows=rows, label=label)


@mcp.tool()
def read_terminal(
    session_id: str,
    since_seq: int = 0,
    max_bytes: int = 20000,
    strip_ansi: bool = True,
    include_input: bool = False,
) -> dict[str, Any]:
    return get_manager().read(
        session_id=session_id,
        since_seq=since_seq,
        max_bytes=max_bytes,
        strip_ansi=strip_ansi,
        include_input=include_input,
    )


@mcp.tool()
def send_text(session_id: str, text: str, submit: bool = False) -> dict[str, Any]:
    return get_manager().send_text(session_id=session_id, text=text, submit=submit)


@mcp.tool()
def send_key(session_id: str, key: str) -> dict[str, Any]:
    return get_manager().send_key(session_id=session_id, key=key)


@mcp.tool()
def resize_terminal(session_id: str, cols: int, rows: int) -> dict[str, Any]:
    return get_manager().resize(session_id=session_id, cols=cols, rows=rows)


@mcp.tool()
def terminal_status(session_id: str) -> dict[str, Any]:
    return get_manager().terminal_status(session_id=session_id)


@mcp.tool()
def close_terminal(session_id: str, mode: str = "terminate") -> dict[str, Any]:
    return get_manager().close(session_id=session_id, mode=mode)


@mcp.tool()
def list_terminals(include_closed: bool = True) -> dict[str, Any]:
    return get_manager().list(include_closed=include_closed)


@mcp.tool()
def export_transcript(session_id: str, format: str = "markdown") -> dict[str, Any]:
    return get_manager().export_transcript(session_id=session_id, format=format)


def main() -> None:
    mcp.run()
```

- [ ] **Step 4: Run all Python tests**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest -v
```

Expected: PASS.

- [ ] **Step 5: Start MCP server manually**

Run:

```bash
cd plugins/terminal-session-mcp && timeout 2 uv run python -m terminal_session_mcp || true
```

Expected: no Python import errors. The command may exit due to timeout; it must not print ordinary logs to stdout before timeout.

- [ ] **Step 6: Commit MCP tools**

```bash
git add plugins/terminal-session-mcp/terminal_session_mcp/server.py \
  plugins/terminal-session-mcp/tests/test_server_tools.py
git commit -m "feat: expose terminal session MCP tools"
```

---

### Task 6: Add skill, slash command, and plugin docs

**Files:**
- Create: `plugins/terminal-session-mcp/skills/terminal-session-debugging/SKILL.md`
- Create: `plugins/terminal-session-mcp/skills/terminal-session-debugging/README.md`
- Create: `plugins/terminal-session-mcp/skills/terminal-session-debugging/README-zh.md`
- Create: `plugins/terminal-session-mcp/commands/terminal-debug.md`
- Create: `plugins/terminal-session-mcp/README.md`
- Create: `plugins/terminal-session-mcp/README-zh.md`

- [ ] **Step 1: Create skill file**

Create `plugins/terminal-session-mcp/skills/terminal-session-debugging/SKILL.md`:

```markdown
---
name: terminal-session-debugging
description: Use when debugging interactive CLI, REPL, TUI, ssh, telnet, nc, watch-mode, dev server, long-running command, terminal prompt flow, or any command that may not exit. Provides a PTY-backed MCP workflow for spawning terminal sessions, sending text and keys, reading output, managing multiple sessions, and exporting full transcripts.
---

# Terminal Session Debugging

Use the `terminal-session` MCP server for terminal programs that need real PTY behavior or may not exit.

## When to Use

Use this workflow for:

- Interactive CLIs, REPLs, shell prompts, installers, wizards, and prompt loops.
- TUI/curses programs where terminal size and key handling matter.
- `ssh`, `telnet`, `nc`, and other bidirectional terminal/network sessions.
- Watch-mode tools, dev servers, and commands that may run forever.
- Multi-session debugging such as server + client, listener + connector, REPL + shell.
- Any task where a normal Bash call may block, hide prompts, or lose interaction history.

## Core Workflow

1. Call `health_check` to confirm the MCP server is available.
2. Call `spawn_terminal` with a clear `label`.
3. Call `read_terminal` to observe initial output.
4. Send one input at a time with `send_text` or `send_key`.
5. Read after every input before deciding the next action.
6. Use `terminal_status` and `list_terminals` to inspect state.
7. Use `resize_terminal` when terminal dimensions matter.
8. Use `close_terminal` to interrupt, send EOF, terminate, or kill sessions.
9. Call `export_transcript` before reporting final results.

## Recording Model

The MCP records command, output, stdin text, key events, resize events, close events, exit status, and errors under `.terminal-debug/`. It does not redact, mask, block, or safety-filter commands or content. Treat transcripts as complete debugging evidence.

## Interaction Discipline

- Do not send a long script of answers until the prompt sequence is known.
- For prompt flows, treat each prompt as a state; capture, send one response, capture again.
- For multiple sessions, use labels such as `server`, `client`, `listener`, `repl`, or `ssh`.
- Never claim a behavior happened unless it appears in `read_terminal`, `terminal_status`, or the exported transcript.

## Report Format

When reporting results, include:

- Session IDs and labels.
- Commands spawned.
- Inputs and keys sent.
- Observed output evidence.
- Interpretation of what the evidence proves.
- Transcript export paths.
- Cleanup status for active sessions.
```

- [ ] **Step 2: Create slash command**

Create `plugins/terminal-session-mcp/commands/terminal-debug.md`:

```markdown
---
description: Start a terminal-session MCP debugging workflow for an interactive or long-running command.
argument-hint: <command or debugging goal>
---

Use the terminal-session MCP to debug this command or scenario: $ARGUMENTS

Workflow:
1. Call health_check.
2. Spawn a terminal session with a clear label.
3. Read initial output.
4. Interact step by step using send_text/send_key.
5. Use terminal_status/list_terminals as needed.
6. Export transcript before finishing.
```

- [ ] **Step 3: Create skill READMEs**

Create `plugins/terminal-session-mcp/skills/terminal-session-debugging/README.md`:

```markdown
# Terminal Session Debugging Skill

Guides Claude Code to use the `terminal-session` MCP server for PTY-backed debugging of interactive and long-running terminal commands.

Use it for REPLs, TUIs, ssh, telnet, nc, watch-mode tools, dev servers, and prompt flows that require sending text or special keys and preserving a full transcript.
```

Create `plugins/terminal-session-mcp/skills/terminal-session-debugging/README-zh.md`:

```markdown
# Terminal Session Debugging Skill

指导 Claude Code 使用 `terminal-session` MCP server 调试基于 PTY 的交互式和长时间运行终端命令。

适用于 REPL、TUI、ssh、telnet、nc、watch mode、dev server，以及需要发送文本/特殊按键并保留完整记录的 prompt flow。
```

- [ ] **Step 4: Create plugin README**

Create `plugins/terminal-session-mcp/README.md`:

```markdown
# terminal-session-mcp

PTY-backed terminal session MCP for Claude Code.

## Features

- Long-running terminal sessions that do not block MCP tool calls
- Interactive text input and special key input
- Multi-session concurrency
- Terminal resize support
- Full bidirectional transcript recording
- Markdown, text, ANSI, and JSONL transcript export
- `uv`-powered stdio MCP launch

## Install

```bash
/plugin install terminal-session-mcp@Esonhugh-Marketplace
```

## MCP Tools

- `health_check`
- `spawn_terminal`
- `read_terminal`
- `send_text`
- `send_key`
- `resize_terminal`
- `terminal_status`
- `close_terminal`
- `list_terminals`
- `export_transcript`

## Examples

### Python REPL

Ask Claude:

```text
Use terminal-session MCP to start `python -i`, send `1+1`, read the result, send Ctrl-D, and export the transcript.
```

### Long-running command

```text
Use terminal-session MCP to start `sleep 9999`, verify it is running, terminate it, and export the transcript.
```

### Multi-session

```text
Use terminal-session MCP to start `python -i` labeled py and `sh` labeled shell. Send commands to both, read both outputs, and export both transcripts.
```

## Storage

Session records are written under the current workspace:

```text
.terminal-debug/
  index.json
  sessions/<session_id>/
    metadata.json
    events.jsonl
    transcript.ansi
    transcript.txt
    summary.md
```

All input and output are recorded exactly as debugging evidence. This plugin does not redact, mask, block, allowlist, or safety-filter terminal content.

## Platform Support

MVP supports macOS and Linux. Windows ConPTY support is not included yet.

## Limitations

- Does not attach to existing terminal tabs or tmux panes.
- Does not implement a full TUI screen model.
- Does not recover active PTY control after MCP server restart.
- Does not automatically record unrelated Bash tool calls.
```

- [ ] **Step 5: Create Chinese plugin README**

Create `plugins/terminal-session-mcp/README-zh.md`:

```markdown
# terminal-session-mcp

面向 Claude Code 的 PTY 终端会话 MCP。

## 功能

- 长时间运行命令不会阻塞 MCP tool call
- 支持交互式文本输入和特殊按键输入
- 支持多 session 并发
- 支持终端 resize
- 完整记录双向交互 transcript
- 支持 Markdown、text、ANSI、JSONL 导出
- 通过 `uv` 以 stdio MCP 方式启动

## 安装

```bash
/plugin install terminal-session-mcp@Esonhugh-Marketplace
```

## MCP Tools

- `health_check`
- `spawn_terminal`
- `read_terminal`
- `send_text`
- `send_key`
- `resize_terminal`
- `terminal_status`
- `close_terminal`
- `list_terminals`
- `export_transcript`

## 示例

### Python REPL

```text
Use terminal-session MCP to start `python -i`, send `1+1`, read the result, send Ctrl-D, and export the transcript.
```

### 长时间运行命令

```text
Use terminal-session MCP to start `sleep 9999`, verify it is running, terminate it, and export the transcript.
```

### 多 session

```text
Use terminal-session MCP to start `python -i` labeled py and `sh` labeled shell. Send commands to both, read both outputs, and export both transcripts.
```

## 存储

记录保存在当前 workspace：

```text
.terminal-debug/
  index.json
  sessions/<session_id>/
    metadata.json
    events.jsonl
    transcript.ansi
    transcript.txt
    summary.md
```

所有输入和输出都会作为调试证据原样记录。本插件不做打码、脱敏、拦截、allowlist 或安全过滤。

## 平台支持

MVP 支持 macOS 和 Linux。暂不支持 Windows ConPTY。

## 限制

- 不附着已有 terminal tab 或 tmux pane。
- 不实现完整 TUI screen model。
- MCP server 重启后不恢复活跃 PTY 控制。
- 不自动记录无关 Bash tool call。
```

- [ ] **Step 6: Commit plugin docs**

```bash
git add plugins/terminal-session-mcp/skills/terminal-session-debugging/SKILL.md \
  plugins/terminal-session-mcp/skills/terminal-session-debugging/README.md \
  plugins/terminal-session-mcp/skills/terminal-session-debugging/README-zh.md \
  plugins/terminal-session-mcp/commands/terminal-debug.md \
  plugins/terminal-session-mcp/README.md \
  plugins/terminal-session-mcp/README-zh.md
git commit -m "docs: add terminal session plugin guidance"
```

---

### Task 7: Update marketplace README files

**Files:**
- Modify: `README.md`
- Modify: `README-zh.md`

- [ ] **Step 1: Add English catalog row**

In `README.md`, add this row after `interactive-cli-systemic-debugging`:

```markdown
| [terminal-session-mcp](#terminal-session-mcp) | Development | Esonhugh | local | PTY terminal session MCP for long-running interactive CLI debugging and full transcript recording |
```

- [ ] **Step 2: Add English plugin section**

In `README.md`, add this section after the `interactive-cli-systemic-debugging` section:

```markdown
### terminal-session-mcp

PTY-backed terminal session MCP server for Claude Code. It runs through `uv` as a stdio MCP server and supports long-running commands, multi-session concurrency, special key input, terminal resizing, and complete bidirectional transcript recording.

```bash
/plugin install terminal-session-mcp@Esonhugh-Marketplace
```

**Included MCP server:** `terminal-session`

**Included Skill:** `terminal-session-debugging`

**Use cases:** debugging REPLs, TUIs, ssh/telnet/nc sessions, watch-mode commands, dev servers, prompt flows, and any terminal command that may not exit or needs real key input.

**Records:** all command input, output, key events, resize events, close events, exit status, and errors under `.terminal-debug/` without redaction or masking.

---
```

- [ ] **Step 3: Add Chinese catalog row**

In `README-zh.md`, add this row after `interactive-cli-systemic-debugging`:

```markdown
| [terminal-session-mcp](#terminal-session-mcp) | 开发 | Esonhugh | 本地 | 基于 PTY 的终端会话 MCP，支持长命令、交互式 CLI 调试和完整记录 |
```

- [ ] **Step 4: Add Chinese plugin section**

In `README-zh.md`, add this section after the `interactive-cli-systemic-debugging` section:

```markdown
### terminal-session-mcp

面向 Claude Code 的 PTY 终端会话 MCP server。它通过 `uv` 以 stdio MCP 方式运行，支持长时间运行命令、多 session 并发、特殊按键输入、终端 resize 和完整双向 transcript 记录。

```bash
/plugin install terminal-session-mcp@Esonhugh-Marketplace
```

**包含的 MCP server：** `terminal-session`

**包含的 Skill：** `terminal-session-debugging`

**适用场景：** 调试 REPL、TUI、ssh/telnet/nc session、watch-mode 命令、dev server、prompt flow，以及任何可能不退出或需要真实按键输入的终端命令。

**记录内容：** 所有 command input、output、key event、resize event、close event、exit status 和 error 都会原样保存到 `.terminal-debug/`，不打码、不脱敏。

---
```

- [ ] **Step 5: Run tests after docs changes**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest -v
```

Expected: PASS.

- [ ] **Step 6: Commit marketplace docs**

```bash
git add README.md README-zh.md
git commit -m "docs: list terminal session MCP plugin"
```

---

### Task 8: Full local verification and Claude CLI verification

**Files:**
- No new source files expected.
- May modify implementation files if tests reveal defects.

- [ ] **Step 1: Run full plugin test suite**

Run:

```bash
cd plugins/terminal-session-mcp && uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run MCP server startup smoke check**

Run:

```bash
cd plugins/terminal-session-mcp && timeout 2 uv run python -m terminal_session_mcp || true
```

Expected: no import traceback. No ordinary log output should appear on stdout.

- [ ] **Step 3: Inspect generated debug artifacts from tests**

Run:

```bash
find plugins/terminal-session-mcp -path '*/.terminal-debug/*' -maxdepth 6 -type f | head -20
```

Expected: tests may create `.terminal-debug` under pytest temp directories, not necessarily under plugin root. If plugin root contains `.terminal-debug` from manual checks, inspect it and remove it only if it was created by this implementation work and is not needed.

- [ ] **Step 4: Run Claude CLI real MCP verification**

Start Claude CLI from the repository root:

```bash
claude
```

In Claude CLI, verify plugin/MCP loading according to the local marketplace/plugin workflow. Then run these prompts:

```text
Use terminal-session MCP health_check and report the result.
```

```text
Use terminal-session MCP to spawn `echo hello-terminal-mcp`, read the output, check status, and export the transcript.
```

```text
Use terminal-session MCP to start `python -i`, wait for the prompt, send `1+1` with Enter, read the result, then send Ctrl-D and export the transcript.
```

```text
Use terminal-session MCP to start `sleep 9999`, verify it is running, then terminate it and check final status.
```

```text
Use terminal-session MCP to start two sessions: `python -i` labeled py and `sh` labeled shell. In py send `10*10`; in shell send `echo shell-ok`; read both outputs and export both transcripts.
```

Expected: Claude CLI can call MCP tools; outputs and transcripts match each scenario; `.terminal-debug` is created in the current workspace.

- [ ] **Step 5: If Claude CLI verification fails, fix and rerun**

Use the failing output to identify the issue. Common fixes:

- If MCP cannot start, inspect `.mcp.json` and `pyproject.toml`.
- If stdout protocol is polluted, remove `print()` and move logs to stderr/file.
- If tools are missing, inspect `server.py` tool decorators.
- If PTY tests pass but Claude CLI fails, verify `${CLAUDE_PLUGIN_ROOT}` expansion and `uv --directory` behavior.

After any fix, rerun:

```bash
cd plugins/terminal-session-mcp && uv run pytest -v
```

Then rerun the relevant Claude CLI scenario.

- [ ] **Step 6: Commit verification fixes or final state**

If Step 5 changed files:

```bash
git add plugins/terminal-session-mcp README.md README-zh.md
git commit -m "fix: verify terminal session MCP plugin"
```

If no files changed, do not create an empty commit.

- [ ] **Step 7: Final status report**

Report:

- Test command and result.
- Claude CLI scenarios completed.
- Transcript paths created.
- Any limitations still present.
- Whether any sessions were left running or all were closed.

---

## Self-Review

### Spec coverage

- Marketplace plugin structure: Tasks 1, 6, 7.
- `uv` stdio MCP config: Task 1.
- PTY simulation: Task 4.
- Long-running nonblocking sessions: Task 4 tests and implementation.
- Multi-session concurrency: Task 4 tests.
- Full bidirectional recording: Task 3 and Task 4.
- Key input: Task 2 keymap and Task 4 PTY send_key.
- Resize: Task 4 PTYSession and tests.
- Export transcript: Task 3 storage and Task 4 manager.
- Skill and slash command: Task 6.
- Claude CLI verification: Task 8.

### Placeholder scan

This plan contains no TBD/TODO/FIXME placeholders. Optional future work from the spec is excluded from MVP except `summarize_terminal`, which is explicitly not required because `export_transcript(format="markdown")` satisfies MVP transcript export.

### Type consistency

The plan consistently uses these names:

- `SessionManager.spawn/read/send_text/send_key/resize/terminal_status/close/list/export_transcript`.
- MCP tools: `health_check`, `spawn_terminal`, `read_terminal`, `send_text`, `send_key`, `resize_terminal`, `terminal_status`, `close_terminal`, `list_terminals`, `export_transcript`.
- Event types: `spawn`, `output`, `input_text`, `input_key`, `resize`, `close`, `exit`, `error`, `orphaned`.
