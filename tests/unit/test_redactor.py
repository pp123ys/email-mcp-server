from email_mcp.security.redactor import redact


def test_redact_secret():
    out = redact("password is hunter2, ok?", ["hunter2"])
    assert "hunter2" not in out
    assert "***" in out


def test_redact_multiple():
    out = redact("a=b c=d", ["b", "d"])
    assert out == "a=*** c=***"
