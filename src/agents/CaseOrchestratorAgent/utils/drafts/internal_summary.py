from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_internal_summary(
    intents: List[Dict[str, Any]],
    topic_keywords: Optional[List[str]],
    action_specs: List[Dict[str, Any]],
    auth_status: str,
) -> str:
    intent_names = [i.get("name") for i in intents or [] if isinstance(i, dict)]
    compact_actions = [
        {
            "type": a.get("action_type"),
            "status": a.get("action_status"),
            "why": (a.get("result") or {}).get("blocked_reason"),
        }
        for a in (action_specs or [])
    ]
    return (
        f"Auth status: {auth_status}\n"
        f"Intents: {intent_names}\n"
        f"Topics: {topic_keywords or []}\n"
        f"Actions: {compact_actions}"
    )
