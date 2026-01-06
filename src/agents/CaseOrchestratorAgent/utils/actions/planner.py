from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.agents.CaseOrchestratorAgent.utils.actions.policy import INTENT_TO_ACTION, ACTION_REQUIRED_ENTITIES


def _compute_missing_entities(required: List[str], entities: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for k in required:
        v = entities.get(k)
        if v is None or v == "" or v == []:
            missing.append(k)
    return missing


def plan_actions_from_extracted_intents(
    intents: List[Dict[str, Any]],
    entities: Dict[str, Any],
    min_confidence: float = 0.60,
) -> List[Dict[str, Any]]:
    """
    No auth logic here. Auth is handled elsewhere.

    Returns action_specs:
    [
      {
        "action_type": "...",
        "action_status": "planned" | "blocked",
        "result": {...}
      },
      ...
    ]
    """
    action_specs: List[Dict[str, Any]] = []

    for intent in intents or []:
        if not isinstance(intent, dict):
            continue

        intent_name = intent.get("name")
        confidence = float(intent.get("confidence") or 0.0)
        reason = intent.get("reason")

        action_type = INTENT_TO_ACTION.get(intent_name)
        if not action_type:
            continue

        if confidence < min_confidence:
            action_specs.append({
                "action_type": action_type,
                "action_status": "blocked",
                "result": {
                    "blocked_reason": "low_confidence_intent",
                    "intent_name": intent_name,
                    "confidence": confidence,
                    "reason": reason,
                },
            })
            continue

        required_entities = ACTION_REQUIRED_ENTITIES.get(action_type, [])
        missing_entities = _compute_missing_entities(required_entities, entities)

        if missing_entities:
            action_specs.append({
                "action_type": action_type,
                "action_status": "blocked",
                "result": {
                    "blocked_reason": "missing_entity",
                    "missing": missing_entities,
                    "intent_name": intent_name,
                    "confidence": confidence,
                    "reason": reason,
                },
            })
            continue

        action_specs.append({
            "action_type": action_type,
            "action_status": "planned",
            "result": {
                "intent_name": intent_name,
                "confidence": confidence,
                "reason": reason,
                "entities_snapshot": {k: entities.get(k) for k in required_entities},
            },
        })

    return action_specs
