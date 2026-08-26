from email_mcp.errors import EmailMCPError, ErrorCode, error_result


def test_error_code_values():
    assert ErrorCode.IMAP_AUTH_FAILED == "IMAP_AUTH_FAILED"
    assert ErrorCode.EMAIL_NOT_FOUND == "EMAIL_NOT_FOUND"
    assert ErrorCode.RATE_LIMITED == "RATE_LIMITED"


def test_exception_holds_fields():
    err = EmailMCPError(ErrorCode.CONFIG_MISSING, "缺少配置")
    assert err.code == ErrorCode.CONFIG_MISSING
    assert str(err) == "缺少配置"


def test_error_result_shape():
    result = error_result(ErrorCode.IMAP_AUTH_FAILED, "认证失败")
    assert result == {
        "success": False,
        "error": {"code": "IMAP_AUTH_FAILED", "message": "认证失败", "details": {}},
    }


def test_error_result_with_details():
    result = error_result(ErrorCode.EMAIL_NOT_FOUND, "未找到", {"id": "INBOX:1"})
    assert result["error"]["details"] == {"id": "INBOX:1"}


def test_unhandled_exception_wraps_to_internal():
    result = EmailMCPError.from_exception(RuntimeError("boom"))
    assert result.code == ErrorCode.INTERNAL
