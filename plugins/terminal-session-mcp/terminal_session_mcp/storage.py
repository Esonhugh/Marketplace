from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from terminal_session_mcp.ansi import strip_ansi
from terminal_session_mcp.models import SessionMetadata
from terminal_session_mcp.timeutil import utc_now_iso

SESSION_ID_RE = re.compile(r"^term_[A-Za-z0-9T_]+_[0-9a-f]{6}$|^term_test$")


class Storage:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.sessions_root = self.root / "sessions"
        self.root.mkdir(parents=True, exist_ok=True)
        self.sessions_root.mkdir(parents=True, exist_ok=True)

    def session_dir(self, session_id: str) -> Path:
        if not SESSION_ID_RE.fullmatch(session_id):
            raise ValueError(f"Invalid session_id: {session_id}")
        path = (self.sessions_root / session_id).resolve()
        sessions_root = self.sessions_root.resolve()
        if path != sessions_root and sessions_root not in path.parents:
            raise ValueError(f"Session path escapes storage root: {session_id}")
        return path

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
