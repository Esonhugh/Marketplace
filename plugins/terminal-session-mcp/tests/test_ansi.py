from terminal_session_mcp.ansi import strip_ansi


def test_strip_color_sequences():
    assert strip_ansi("\x1b[31mred\x1b[0m") == "red"


def test_strip_cursor_sequences():
    assert strip_ansi("hello\x1b[2K\rworld") == "hello\rworld"


def test_plain_text_is_unchanged():
    assert strip_ansi("plain text") == "plain text"
