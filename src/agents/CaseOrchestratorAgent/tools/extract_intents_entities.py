import asyncio
import logging
from uuid import UUID

# from src.agents.CaseOrchestratorAgent.tools.auth_policy_evaluator import auth_policy_evaluator
from src.agents.CaseOrchestratorAgent.tools.case_resolver import case_resolver
from src.agents.CaseOrchestratorAgent.tools.message_writer import message_writer
from src.models.ExtractionsModel import ExtractionsModel
from src.models.db_schemes import Extractions
from src.logs.log import build_logger
from src.utils.client_deps_container import DependencyContainer


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

    # 5) Full prompt: doc + footer
    full_prompt = "\n\n".join([document_prompt, footer_prompt])

    # 6) Generate
    answer, total_tokens, cost =container.generation_client.generate_text(
        prompt=full_prompt,
        chat_history=chat_history,
    )


    # print raw model output
    log.debug("="*20)


    # parse json
    llm_answer = _parse_json_strict(answer)
    # 8) enforce the required keys
    _validate_extraction_schema(llm_answer)

    log.debug("\n--- LLMs JSON ---")
    log.debug(json.dumps(llm_answer, indent=2))


    return llm_answer




def _parse_json_strict(text: str) -> Dict[str, Any]:
    """
    Strict JSON parse.
    Also handles the common case where the model returns JSON wrapped with whitespace.
    """
    text = text.strip()

    # Try direct JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to salvage
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            return json.loads(candidate)

        raise


def _validate_extraction_schema(obj: Dict[str, Any]) -> None:
    """
    Minimal validation to catch broken outputs early.
    Extend later with Pydantic if you want.
    """
    required_top_keys = {
        "case_id",
        "message_id",
        "language",
        "intents",
        "entities",
        "overall_confidence",
        "needs_followup",
        "missing_fields_for_next_step",
        "notes_for_agent",
    }

    missing = required_top_keys - set(obj.keys())
    if missing:
        raise ValueError(f"Extraction JSON missing keys: {sorted(missing)}")

    if not isinstance(obj["intents"], list):
        raise ValueError("intents must be a list")

    if not isinstance(obj["entities"], dict):
        raise ValueError("entities must be a dict")




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






async def main():
    container = await DependencyContainer.create()
    template_parser = container.template_parser
    generation_model_client = container.generation_client

    emails = [
        {
            "from_email": "customer@example.com",
            "subject": "Meter reading",
            "body": "Hello, my meter reading is 12345. and Can you explain the dynamic tariff?",
        },
        {
            "from_email": "customer@example.com",
            "subject": "Re: Meter reading [CASE: 39dd8ad7-13ee-4735-ab3e-635fcd0bd39b]",
            "body": "Here is the missing info you asked for.",
        },
        {
            "from_email": "customer@example.com",
            "subject": "Re: Meter reading",
            "body": "Another follow-up without token.",
        },
        {
            "from_email": "other@example.com",
            "subject": "Tariff question",
            "body": "Can you explain the dynamic tariff?",
        },
    ]

    case = await case_resolver(
        container=container,
        from_email=emails[0]["from_email"],
        subject=emails[0]["subject"],
        body=emails[0]["body"],
    )

    msg = await message_writer(
        container=container,
        case_uuid=case.case_uuid,  # IMPORTANT: use case_uuid
        direction="inbound",
        subject=emails[0]["subject"],
        body=emails[0]["body"],
        from_email=emails[0]["from_email"],
    )

    llms_intents_entities= await extract_intents_entities(
        case_id=case.case_uuid,
        message_id=msg.message_id,
        from_email=emails[0]["from_email"],
        subject=emails[0]["subject"],
        body=emails[0]["body"],
    )

    write_intents_entities = await save_extraction(
        container=container,
        llm_result=llms_intents_entities)

    #auth_required = auth_policy_evaluator(intents=llms_intents_entities["intents"])

    #print(auth_required)



if __name__ == "__main__":
    asyncio.run(main())