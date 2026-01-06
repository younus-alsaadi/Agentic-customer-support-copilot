from typing import Literal, Optional
import re

Direction = Literal["inbound", "outbound"]

RE_PREFIX_RE = re.compile(r"^(re:|fw:|fwd:)\s*", re.IGNORECASE)

def normalize_subject_for_matching(subject: Optional[str]) -> str:
    """
    ONLY for matching / resolver logic.
    """
    if not subject:
        return ""
    s = subject.strip()
    s = RE_PREFIX_RE.sub("", s).strip()
    return s.lower()
