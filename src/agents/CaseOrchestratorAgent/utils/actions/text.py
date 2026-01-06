from __future__ import annotations

def humanize_field(x: str) -> str:
    return x.replace("_", " ").strip()
