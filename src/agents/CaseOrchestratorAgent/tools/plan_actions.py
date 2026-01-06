from __future__ import annotations
import logging
from src.agents.CaseOrchestratorAgent.utils.actions.planner import plan_actions_from_extracted_intents
from src.agents.CaseOrchestratorAgent.utils.actions.serialize_actions import action_to_dict
from src.agents.CaseOrchestratorAgent.utils.drafts.final_reply_draft import build_option1_public_text, \
    build_option2_missing_info_text, build_option3_processing_text
from src.agents.CaseOrchestratorAgent.utils.drafts.internal_summary import build_internal_summary
from src.agents.CaseOrchestratorAgent.utils.drafts.serialize_drafts import draft_to_dict
from src.agents.CaseOrchestratorAgent.utils.uuid_utils import to_uuid
from src.logs.log import build_logger
from src.models.ActionsModel import ActionsModel
from src.models.CasesModel import CasesModel
from src.models.DraftsModel import DraftsModel
from uuid import UUID
from typing import Any, Dict, List, Optional

log = build_logger(level=logging.DEBUG)


async def plan_actions_and_create_final_draft(
    container,
    case_id: UUID,  # can also come as str from state
    intents: List[Dict[str, Any]],
    entities: Dict[str, Any],
    topic_keywords: Optional[List[str]],
    auth_status: Optional[str] = None,  # "no_need" OR "success" (etc.)
) -> Dict[str, Any]:
    """
    Safe for parallel calls:
    - non-auth node writes option1
    - auth node writes option2 OR option3 (+ actions)
    Both update the SAME draft row without losing content.
    """

    print("\n" + "+#" * 80)
    print("[plan_actions_and_create_final_draft] START")
    print("case_id:", case_id)
    print("auth_status:", auth_status)
    print("topic_keywords:", topic_keywords)
    print("intents:", [i.get("name") for i in (intents or []) if isinstance(i, dict)])
    print("=" * 80)

    # -------------------------
    # start
    # -------------------------
    case_uuid = to_uuid(case_id)
    entities = entities or {}
    topic_keywords = topic_keywords or []

    actions_model = await ActionsModel.create_instance(db_client=container.db_client)
    drafts_model = await DraftsModel.create_instance(db_client=container.db_client)
    cases_model = await CasesModel.create_instance(db_client=container.db_client)

    # Decide which option text we produce in THIS call
    new_reply_draft_text = ""
    action_specs: List[Dict[str, Any]] = []
    created_actions = []

    if auth_status == "no_need":
        # Option 1 only (public info)
        new_reply_draft_text = build_option1_public_text(topic_keywords)

    else:
        # Option 2 OR 3 (backend flow)
        action_specs = plan_actions_from_extracted_intents(intents=intents, entities=entities)

        if any(a.get("action_status") == "blocked" for a in action_specs):
            new_reply_draft_text = build_option2_missing_info_text(action_specs)
        else:
            new_reply_draft_text = build_option3_processing_text(action_specs, intents)

    print("\n[option_select]")
    print("new_reply_draft_text (len):", len(new_reply_draft_text or ""))
    print("new_reply_draft_text (preview):", (new_reply_draft_text or "")[:250])


    subject_topic = topic_keywords[0] if topic_keywords else "Your request"
    customer_reply_subject = f"Re: {subject_topic} [CASE: {case_uuid}]"

    # Build internal summary (only meaningful when action_specs exist)
    internal_summary = build_internal_summary(
        intents=intents,
        topic_keywords=topic_keywords,
        action_specs=action_specs,
        auth_status=auth_status or "",
    )


    # Draft upsert/merge (parallel-safe)
    draft = await drafts_model.upsert_public_reply_draft_merge(
        case_uuid=case_uuid,
        new_reply_draft_text=new_reply_draft_text,
        customer_reply_subject=customer_reply_subject,
        internal_summary=internal_summary,
        action_specs=action_specs if action_specs else None,
        draft_type="public_reply",
        max_attempts=2,
    )

    # -------------------------
    # Actions rows (ONLY for auth flow)
    # -------------------------
    if auth_status != "no_need" and action_specs:
        created_actions = await actions_model.insert_many_actions(case_id=case_uuid, action_specs=action_specs)

    # -------------------------
    # Case status (both nodes may call it; it’s okay)
    # -------------------------
    await cases_model.update_case_status_by_uuid(
        case_uuid=case_uuid,
        new_status="pending_review",
        status_meta={
            "stage": "final_draft_ready",
            "action_ids": [str(a.id) for a in (created_actions or [])],
            "auth_status": auth_status,
        },
    )

    return {
        "ok": True,
        "case_uuid": str(case_uuid),
        "draft": draft_to_dict(draft),
        "case_status": "pending_review",
        "actions_created": [action_to_dict(a) for a in (created_actions or [])],
        "action_specs": action_specs,
    }
