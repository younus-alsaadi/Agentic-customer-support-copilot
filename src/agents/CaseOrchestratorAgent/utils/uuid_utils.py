from __future__ import annotations

from uuid import UUID

def to_uuid(x) -> UUID:
    if isinstance(x, UUID):
        return x
    return UUID(str(x))
