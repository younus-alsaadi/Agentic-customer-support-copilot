from __future__ import annotations

from typing import Any, Dict, Optional

from src.utils.pii_safe import hash_field, mask_value


def is_empty(v: Any) -> bool:
    return v is None or v == "" or v == {} or v == "null"


def norm_str(v: Any) -> Optional[str]:
    if is_empty(v):
        return None
    s = str(v).strip()
    return s or None


def to_safe_field(raw: Optional[str], *, salt: str) -> Optional[Dict[str, str]]:
    if not raw:
        return None
    return {"hash": hash_field(raw, salt=salt), "masked": mask_value(raw)}


def safe_hash(v: Optional[str], salt: str) -> Optional[str]:
    if not v:
        return None
    return hash_field(v, salt=salt)

def get_hash_from_stored(stored_fields: Dict[str, Any], key: str) -> Optional[str]:
    v = stored_fields.get(key)
    if isinstance(v, dict):
        h = v.get("hash")
        if isinstance(h, str) and h:
            return h
    return None
