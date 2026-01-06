import asyncio
import logging
from uuid import UUID

from src.agents.CaseOrchestratorAgent.utils.llm.validate_llm_response import parse_json_strict, validate_extraction_schema
from src.models.ExtractionsModel import ExtractionsModel
from src.models.db_schemes import Extractions
from src.logs.log import build_logger


log = build_logger(level=logging.DEBUG)


import json
from typing import Any, Dict, Optional


async def extract_intents_entities(
    container,
    from_email: str,
    subject: Optional[str],
    body: str,
) -> Dict[str, Any]:
    """
    Build prompts from templates and extract structured intents/entities.
    Returns a dict parsed from JSON (no free text).
    """

    # 1) Load templates
    system_prompt = container.template_parser.get_template_from_locales(
        "extract_intents", "system_prompt"
    )

    # 2) Build document prompt (email content)
    document_prompt = container.template_parser.get_template_from_locales(
        "extract_intents",
        "document_prompt",
        {
            "from_email": from_email,
            "subject": subject or "",
            "chunk_text": body,
        },
    )

    # 3) Build footer (schema + few-shot + task variables)
    footer_prompt = container.template_parser.get_template_from_locales(
        "extract_intents",
        "footer_prompt"
    )

    # 4) Chat history: system message only
    chat_history = [
        container.generation_client.construct_prompt(
            prompt=system_prompt,
            role=container.generation_client.enums.SYSTEM.value,
        )
    ]

    log.debug(f"chat_history is {chat_history}")
    log.debug("="*20)

    # 5) Full prompt: doc + footer
    full_prompt = "\n\n".join([document_prompt, footer_prompt])

    log.debug(f"Full prompt: is {full_prompt}")
    log.debug("=" * 20)

    # 6) Generate
    answer, total_tokens, cost = await asyncio.to_thread(
        container.generation_client.generate_text,
        full_prompt,
        chat_history,
    )

    # parse json
    llm_answer = parse_json_strict(answer)
    # 8) enforce the required keys
    validate_extraction_schema(llm_answer)

    log.debug("\n--- LLMs JSON ---")
    log.debug(json.dumps(llm_answer, indent=2))


    return llm_answer


async def save_extraction(
    container,
    case_id,
    message_id,
    llm_result
) -> Extractions:

    for k in ("case_id", "message_id", "intents", "entities", "overall_confidence"):
        if k not in llm_result:
            raise ValueError(f"llm_result missing required key: {k}")

    # Convert IDs to UUID objects (DB uses UUID type)
    case_id = UUID(str(case_id))
    message_id = UUID(str(message_id))


    intents = llm_result["intents"]
    entities = llm_result["entities"]

    conf = llm_result.get("overall_confidence", None)
    confidence = float(conf) if conf is not None else None
    if confidence is not None:
        confidence = max(0.0, min(1.0, confidence))  # clamp 0..1

    extraction_model = await ExtractionsModel.create_instance(db_client=container.db_client)

    extraction_row = Extractions(
        case_id=case_id,
        message_id=message_id,
        intents=intents,
        entities=entities,
        confidence=confidence,
    )

    try:
        new_extraction = await extraction_model.create_extraction(extraction=extraction_row)
        log.debug("inser done {}".format(new_extraction))
    except Exception:
        log.exception("Extraction creation failed")
        raise

    return new_extraction