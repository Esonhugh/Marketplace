from __future__ import annotations

import os
import secrets
import threading
from pathlib import Path
from typing import Any

from terminal_session_mcp.ansi import strip_ansi as strip_ansi_text
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
            prepared = dict(event)
            if strip_ansi and prepared.get("type") == "output" and "text" in prepared:
                prepared["text"] = strip_ansi_text(prepared["text"])
            size = len(str(prepared).encode("utf-8"))
            if returned and total + size > max_bytes:
                truncated = True
                break
            returned.append(prepared)
            total += size
            latest = prepared["seq"]
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
