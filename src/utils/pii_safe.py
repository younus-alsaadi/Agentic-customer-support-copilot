import hashlib
import re
from typing import Optional


def _canon(s: str) -> str:
    # canonicalize for stable hashing
    return re.sub(r"\s+", "", s).strip().lower()


def hash_field(value: Optional[str], salt: str) -> Optional[str]:
    if not value:
        return None
    raw = (salt + "|" + _canon(value)).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def mask_value(value: Optional[str], keep_last: int = 2) -> Optional[str]:
    if not value:
        return None
    v = re.sub(r"\s+", "", str(value))
    if len(v) <= keep_last:
        return "*" * len(v)
    return "*" * (len(v) - keep_last) + v[-keep_last:]