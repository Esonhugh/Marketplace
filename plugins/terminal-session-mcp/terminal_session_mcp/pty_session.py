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
        self._exit_recorded = False

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
        normalized = key.strip().upper()
        payload = key_to_bytes(normalized)
        written = self._write(payload)
        event = self.recorder.record_event("input_key", {"key": normalized, "bytes": written})
        return {"session_id": self.metadata.session_id, "key": normalized, "bytes_written": written, "recorded_seq": event["seq"]}

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
                self._record_exit_once()
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
                self._record_exit_once()
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
            if self.child is None or self._exit_recorded:
                return
            if self.metadata.status not in {STATUS_RUNNING, STATUS_FAILED, STATUS_CLOSED}:
                return
            self._exit_recorded = True
            exit_code = self.child.exitstatus
            signal_status = self.child.signalstatus
            self.recorder.record_event("exit", {"exit_code": exit_code, "signal": signal_status})

    def _require_child(self) -> None:
        if self.child is None:
            raise RuntimeError(f"Session {self.metadata.session_id} has not been spawned")
