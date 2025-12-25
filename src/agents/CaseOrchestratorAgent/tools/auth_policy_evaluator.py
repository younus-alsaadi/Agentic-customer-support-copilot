
import logging

from src.logs.log import build_logger
log = build_logger(level=logging.DEBUG)


"""
  "intents": [
    {
      "name": "MeterReadingSubmission",
      "confidence": 0.95,
      "requires_auth": true,
      "reason": "Customer submits meter reading."
    },
    {
      "name": "ProductInfoRequest",
      "confidence": 0.9,
      "requires_auth": false,
      "reason": "Customer asks about dynamic tariff."
    }
  ],
  "entities": {
    "contract_number": null,
    "meter_number": null,
    "meter_reading_value": 12345,
    "meter_reading_date": null,
    "customer_full_name": null,
    "postal_code": null,
    "address": null,
    "birthdate": null,
    "installment_amount": null,
    "tariff_name": "dynamic",
    "topic_keywords": [
      "dynamic tariff",
      "meter reading"
    ]
  },
  
  needs_followup": true,
  "missing_fields_for_next_step": [
    "contract_number_or_postal_code"
  ],
  "notes_for_agent": "Auth needed for meter reading submission."
  
"""

from typing import Dict, Any, List, Tuple

SENSITIVE_INTENTS = {
    "MeterReadingSubmission",
    "MeterReadingCorrection",
    "PersonalDataChange",
    "ContractIssue",
}

DEFAULT_REQUIRED_FIELDS = ["contract_number", "postal_code"]

from typing import Dict, Any, List

def get_non_auth_intents(intents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Return only intents that do NOT require authentication.

    Input example (intents):
      [{"name": "...", "requires_auth": True/False, "confidence": 0.9, "reason": "..."}]

    Output:
      [{"name": "...", "confidence": 0.9, "requires_auth": False, "reason": "..."}]
    """
    non_auth = []
    for intent in intents or []:
        if not isinstance(intent, dict):
            continue

        requires_auth = bool(intent.get("requires_auth", False))
        if requires_auth:
            continue

        non_auth.append({
            "name": intent.get("name") or "Other",
            "confidence": intent.get("confidence"),
            "requires_auth": False,
            "reason": intent.get("reason"),
        })

    return non_auth
