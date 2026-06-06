from __future__ import annotations

import re

ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)
