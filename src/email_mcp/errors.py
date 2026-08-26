from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    # 配置
    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"
    AUTH_UNSUPPORTED = "AUTH_UNSUPPORTED"
    # 认证
    IMAP_AUTH_FAILED = "IMAP_AUTH_FAILED"
    SMTP_AUTH_FAILED = "SMTP_AUTH_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"  # 预留 OAuth
    # 连接
    IMAP_CONNECT_FAILED = "IMAP_CONNECT_FAILED"
    SMTP_CONNECT_FAILED = "SMTP_CONNECT_FAILED"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    # 操作
    EMAIL_NOT_FOUND = "EMAIL_NOT_FOUND"
    FOLDER_NOT_FOUND = "FOLDER_NOT_FOUND"
    ATTACHMENT_NOT_FOUND = "ATTACHMENT_NOT_FOUND"
    INVALID_RECIPIENT = "INVALID_RECIPIENT"
    EMAIL_TOO_LARGE = "EMAIL_TOO_LARGE"
    # 限流
    RATE_LIMITED = "RATE_LIMITED"
    BATCH_LIMIT_EXCEEDED = "BATCH_LIMIT_EXCEEDED"
    # 兜底
    INTERNAL = "INTERNAL"


class EmailMCPError(Exception):
    """结构化业务错误。"""

    def __init__(self, code: ErrorCode, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    @classmethod
    def from_exception(cls, exc: Exception) -> "EmailMCPError":
        return cls(ErrorCode.INTERNAL, f"内部错误: {exc}")


def error_result(
    code: ErrorCode, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """所有 MCP 工具统一返回的结构化错误。"""
    return {
        "success": False,
        "error": {"code": str(code), "message": message, "details": details or {}},
    }
