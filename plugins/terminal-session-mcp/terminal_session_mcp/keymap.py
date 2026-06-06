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
