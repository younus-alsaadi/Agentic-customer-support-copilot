from __future__ import annotations

def draft_to_dict(draft):
    if not draft:
        return None
    return {
        "id": str(draft.id),
        "case_id": str(draft.case_id),
        "draft_type": draft.draft_type,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
        "updated_at": draft.updated_at.isoformat() if draft.updated_at else None,
    }
