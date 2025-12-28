# Plan actions for the intents
#
# When auth is success (or no auth needed)


from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.logs.log import build_logger
from src.models.ActionsModel import ActionsModel
from src.models.CasesModel import CasesModel
from src.models.DraftsModel import DraftsModel
from src.models.db_schemes import Actions
log = build_logger(level=logging.DEBUG)

# Map intent name -> action_type (only for intents that need a backend action)
INTENT_TO_ACTION: Dict[str, str] = {
    "MeterReadingSubmission": "submit_meter_reading",
    "PersonalDataChange": "update_personal_data",
    "ContractIssues": "handle_contract_issue",
    # Add more...
}

# If an action needs specific entities, declare them here
ACTION_REQUIRED_ENTITIES: Dict[str, List[str]] = {
    "submit_meter_reading": ["meter_reading_value"],  # add meter_number/date if required
    "update_personal_data": [],                       # depends on my needs
    "handle_contract_issue": [],                      # depends on my needs
}

# Safety override: even if LLM mistakenly says requires_auth=False, i can force auth here
ALWAYS_SENSITIVE_ACTIONS = {"submit_meter_reading", "update_personal_data", "handle_contract_issue"}





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
    auth_status: str,            # "success" | "missing" | "failed"
    min_confidence: float = 0.60 # safety gate
) -> List[Dict[str, Any]]:
    """
    Returns action_specs:
    [
      {
        "action_type": "submit_meter_reading",
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
        requires_auth_llm = bool(intent.get("requires_auth", False))
        reason = intent.get("reason")

        # Map intent -> action (skip info-only intents like ProductInfoRequest)
        action_type = INTENT_TO_ACTION.get(intent_name)
        if not action_type:
            continue

        # Confidence gate
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

        # Auth gate (LLM says requires_auth, plus server-side override)
        requires_auth = requires_auth_llm or (action_type in ALWAYS_SENSITIVE_ACTIONS)
        if requires_auth and auth_status != "success":
            action_specs.append({
                "action_type": action_type,
                "action_status": "blocked",
                "result": {
                    "blocked_reason": "auth_missing",
                    "intent_name": intent_name,
                    "confidence": confidence,
                    "reason": reason,
                },
            })
            continue

        # Entity validation
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

        # Ready to run later
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

# ---------- Draft building (template; plug LLM later if you want) ----------

def build_customer_reply_draft(
    intents: List[Dict[str, Any]],
    entities: Dict[str, Any],
    topic_keywords: Optional[List[str]],
    action_specs: List[Dict[str, Any]],
) -> str:
    """
    Simple template draft. later use llm
    """
    lines: List[str] = ["Hello,", ""]

    if topic_keywords:
        lines.append(f"I understood your request about: {', '.join(topic_keywords)}.")
        lines.append("")

    if not action_specs:
        # Example: ProductInfoRequest only (no actions created)
        lines += [
            "Thanks for your message.",
            "We are reviewing it and will respond shortly.",
            "",
            "Kind regards",
        ]
        return "\n".join(lines)

    planned = [a for a in action_specs if a.get("action_status") == "planned"]
    blocked = [a for a in action_specs if a.get("action_status") == "blocked"]

    if planned:
        lines.append("We can proceed with the following:")
        for a in planned:
            lines.append(f"- {a.get('action_type')}")
        lines.append("")

    if blocked:
        lines.append("We still need something before we can continue:")
        for a in blocked:
            res = a.get("result") or {}
            reason = res.get("blocked_reason", "blocked")
            if reason == "missing_entity":
                missing = res.get("missing", [])
                lines.append(f"- {a.get('action_type')}: missing {', '.join(missing)}")
            elif reason == "auth_missing":
                lines.append(f"- {a.get('action_type')}: identity verification required")
            elif reason == "low_confidence_intent":
                lines.append(f"- {a.get('action_type')}: please confirm your request (unclear message)")
            else:
                lines.append(f"- {a.get('action_type')}: {reason}")
        lines.append("")

    lines.append("Kind regards")
    return "\n".join(lines)


def build_internal_summary(
    intents: List[Dict[str, Any]],
    topic_keywords: Optional[List[str]],
    action_specs: List[Dict[str, Any]],
    auth_status: str,
) -> str:
    intent_names = [i.get("name") for i in intents or [] if isinstance(i, dict)]
    compact_actions = [
        {"type": a.get("action_type"), "status": a.get("action_status"), "why": (a.get("result") or {}).get("blocked_reason")}
        for a in action_specs
    ]
    return (
        f"Auth status: {auth_status}\n"
        f"Intents: {intent_names}\n"
        f"Topics: {topic_keywords or []}\n"
        f"Actions: {compact_actions}"
    )


# ---------- Step E main function ----------

async def step_e_plan_actions_and_create_final_draft(
    container,
    case_uuid: UUID,
    intents: List[Dict[str, Any]],
    entities: Dict[str, Any],
    topic_keywords: Optional[List[str]],
    auth_status: str,  # "success" | "missing" | "failed"
) -> Dict[str, Any]:
    """
    Step E:
    - Create Actions rows (planned/blocked)
    - Create/update Drafts (final customer reply + internal summary + action_specs)
    - Set case_status = "pending_review"
    """

    actions_model = await ActionsModel.create_instance(db_client=container.db_client)
    drafts_model = await DraftsModel.create_instance(db_client=container.db_client)
    cases_model = await CasesModel.create_instance(db_client=container.db_client)

    # 1) Plan actions (deterministic)
    action_specs = plan_actions_from_extracted_intents(
        intents=intents,
        entities=entities or {},
        auth_status=auth_status,
    )

    # 2) Store actions (one row per action)
    action_ids: List[str] = []
    for spec in action_specs:
        row = Actions(
            case_id=case_uuid,
            action_type=spec["action_type"],
            action_status=spec["action_status"],
            result=spec.get("result"),
            created_at=datetime.utcnow(),
        )
        created = await actions_model.create_action(action=row)
        action_ids.append(str(getattr(created, "id", "")))

    # 3) Build final draft (template now)
    customer_reply = build_customer_reply_draft(
        intents=intents,
        entities=entities or {},
        topic_keywords=topic_keywords,
        action_specs=action_specs,
    )
    internal_summary = build_internal_summary(
        intents=intents,
        topic_keywords=topic_keywords,
        action_specs=action_specs,
        auth_status=auth_status,
    )

    # 4) Upsert Drafts (you should have DraftsModel.upsert_by_case_id)
    draft = await drafts_model.upsert_by_case_id(
        case_id=case_uuid,
        payload={
            "customer_reply_draft": customer_reply,
            "internal_summary": internal_summary,
            "actions_suggested": action_specs,
            "updated_at": datetime.utcnow(),
        },
    )

    # 5) Update case to pending_review
    await cases_model.update_case_status_by_uuid(
        case_uuid=case_uuid,
        new_status="pending_review",
        status_meta={
            "stage": "final_draft_ready",
            "action_ids": action_ids,
            "auth_status": auth_status,
        },
    )

    log.info(
        "Step E done",
        extra={
            "case_uuid": str(case_uuid),
            "action_count": len(action_specs),
            "draft_id": str(getattr(draft, "id", "")) if draft else None,
        },
    )

    return {
        "ok": True,
        "case_uuid": str(case_uuid),
        "action_ids": action_ids,
        "draft_id": str(getattr(draft, "id", "")) if draft else None,
        "case_status": "pending_review",
        "actions_suggested": action_specs,
    }


