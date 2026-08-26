"""引用块生成。"""
from __future__ import annotations


def build_quote_block(sender: str, date_str: str, original_body: str) -> str:
    """生成 'On ... wrote:' 风格引用块。"""
    lines = []
    for line in (original_body or "").splitlines():
        lines.append(f"> {line}")
    header = f"On {date_str} {sender} wrote:"
    return header + "\n" + "\n".join(lines)
