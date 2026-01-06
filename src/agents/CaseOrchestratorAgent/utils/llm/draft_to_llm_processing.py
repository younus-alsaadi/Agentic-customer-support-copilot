import re
from typing import List

SEPARATOR = "====="

# lines that look like internal logs / intent dumps
_INTERNAL_LINE_RE = re.compile(
    r"(requires_auth|auth_status|confidence|reason:|\{\'name\'|\[\'name\'|\"name\"|\"confidence\")",
    re.IGNORECASE,
)

_WS_RE = re.compile(r"\s+")


def _split_blocks(text: str) -> List[str]:
    return [p.strip() for p in (text or "").split(SEPARATOR) if p.strip()]


def _drop_internal_lines(block: str) -> str:
    kept = []
    for ln in (block or "").splitlines():
        if _INTERNAL_LINE_RE.search(ln):
            continue
        kept.append(ln)
    # normalize whitespace
    cleaned = "\n".join(kept).strip()
    cleaned = re.sub(r"[ \t]+", " ", cleaned)  # avoid weird spacing
    return cleaned.strip()


def _remove_empty_regarding_line(block: str) -> str:
    """
    Sometimes after removing internal lines you end up with:
    'Regarding the about '  (empty / useless)
    Remove that line if it became meaningless.
    """
    lines = [ln.rstrip() for ln in (block or "").splitlines()]
    out = []
    for ln in lines:
        low = ln.strip().lower()
        if low.startswith("regarding") and len(low) < 25:
            # too short to be meaningful after cleaning
            continue
        out.append(ln)
    return "\n".join(out).strip()


def _dedupe_blocks(blocks: List[str]) -> List[str]:
    seen = set()
    out = []
    for b in blocks:
        key = _WS_RE.sub(" ", b.lower()).strip()
        if key and key not in seen:
            seen.add(key)
            out.append(b)
    return out


def normalize_and_dedupe_draft(draft_customer_reply: str) -> str:
    blocks = _split_blocks(draft_customer_reply)

    cleaned_blocks = []
    for b in blocks:
        b = _drop_internal_lines(b)
        b = _remove_empty_regarding_line(b)
        if b:
            cleaned_blocks.append(b)

    cleaned_blocks = _dedupe_blocks(cleaned_blocks)
    return f"\n\n{SEPARATOR}\n\n".join(cleaned_blocks)
