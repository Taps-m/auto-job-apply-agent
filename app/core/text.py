"""Input normalisation shared by all modules."""
import re


def clean_list(value, item_limit: int = 80, max_items: int = 100) -> list:
    """Accept a list or comma-separated string; trim, de-duplicate case-insensitively."""
    if isinstance(value, str):
        value = value.split(",")
    out, seen = [], set()
    for v in value or []:
        s = re.sub(r"\s+", " ", str(v)).strip()[:item_limit]
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out[:max_items]


def text(value, limit: int) -> str:
    return str(value or "").strip()[:limit]
