from __future__ import annotations

import threading
from collections import deque
from typing import Any

from terminal_session_mcp.ansi import strip_ansi as strip_ansi_text
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
                prepared["text"] = strip_ansi_text(prepared["text"])
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
