from dataclasses import dataclass
from typing import List


@dataclass
class EvalItem:
    query: str
    ground_truth_answer: str
    ground_truth_doc_ids: List[str]