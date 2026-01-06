from __future__ import annotations

def action_to_dict(a) -> dict:
    return {
        "id": str(a.id),
        "case_id": str(a.case_id),
        "action_type": getattr(a, "action_type", None),
        "status": getattr(a, "status", None),
        "payload": getattr(a, "payload", None),
        "created_at": a.created_at.isoformat() if getattr(a, "created_at", None) else None,
    }