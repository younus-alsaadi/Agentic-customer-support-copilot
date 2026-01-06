import json
from typing import Optional, Tuple



def parse_llm_email_json(answer: str) -> Optional[Tuple[str, str]]:
    """
    Parse LLM output that MUST be exactly:

    {
      "subject": "string",
      "body": "string"
    }

    Returns:
        (subject, body) if valid
        None if invalid in ANY way
    """

    if not answer or not isinstance(answer, str):
        return None

    text = answer.strip()

    # Reject markdown / code fences
    if text.startswith("```") or text.endswith("```"):
        return None

    def _load_strict(s: str) -> Optional[Tuple[str, str]]:
        try:
            obj = json.loads(s)
        except Exception:
            return None

        if not isinstance(obj, dict):
            return None

        # Must contain EXACTLY these keys
        if set(obj.keys()) != {"subject", "body"}:
            return None

        subject = obj.get("subject")
        body = obj.get("body")

        if not isinstance(subject, str) or not subject.strip():
            return None
        if not isinstance(body, str) or not body.strip():
            return None

        return subject.strip(), body.strip()

    # 1) Try direct parse
    parsed = _load_strict(text)
    if parsed:
        return parsed

    # 2) Salvage: extract single JSON object if wrapped in text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return _load_strict(text[start : end + 1])

    return None