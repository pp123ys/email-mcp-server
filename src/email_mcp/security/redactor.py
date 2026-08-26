from __future__ import annotations

from collections.abc import Iterable


def redact(text: str, secrets: Iterable[str]) -> str:
    """把 secrets 中出现的所有子串替换为 ***。"""
    out = text
    for secret in secrets:
        if secret:
            out = out.replace(secret, "***")
    return out
