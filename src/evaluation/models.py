from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class EvalItem:
    email_subject: str
    email_budy: str
    ground_truth_output: Dict[str, Any]