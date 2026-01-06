from __future__ import annotations

from typing import Dict, List

INTENT_TO_ACTION: Dict[str, str] = {
    "MeterReadingSubmission": "submit_meter_reading",
    "PersonalDataChange": "update_personal_data",
    "ContractIssues": "handle_contract_issue",
}

ACTION_REQUIRED_ENTITIES: Dict[str, List[str]] = {
    "submit_meter_reading": ["meter_number", "meter_reading_value", "meter_reading_date"],
    "update_personal_data": [],
    "handle_contract_issue": [],
}
