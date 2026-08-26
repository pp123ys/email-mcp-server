"""收件人校验。"""
from __future__ import annotations

from email_validator import EmailNotValidError, validate_email

from email_mcp.errors import EmailMCPError, ErrorCode


def validate_recipients(to: list[str], cc: list[str] | None = None) -> None:
    """校验收件人地址，非法时抛 INVALID_RECIPIENT。"""
    bad: list[str] = []
    for addr in list(to) + list(cc or []):
        try:
            validate_email(addr, check_deliverability=False)
        except EmailNotValidError:
            bad.append(addr)
    if bad:
        raise EmailMCPError(
            ErrorCode.INVALID_RECIPIENT,
            f"非法收件人: {bad}",
            {"invalid": bad},
        )
