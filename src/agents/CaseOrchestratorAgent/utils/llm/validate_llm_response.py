import json
from typing import Dict, Any


def parse_json_strict(text: str) -> Dict[str, Any]:
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


def validate_extraction_schema(obj: Dict[str, Any]) -> None:
    """
    Minimal validation to catch broken outputs early.
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

