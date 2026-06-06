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
