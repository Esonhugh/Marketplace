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
