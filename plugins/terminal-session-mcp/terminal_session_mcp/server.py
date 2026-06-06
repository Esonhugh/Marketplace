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
