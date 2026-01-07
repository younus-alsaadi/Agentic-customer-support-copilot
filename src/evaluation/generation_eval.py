from typing import List, Dict, Any, Callable
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import context_precision, context_recall, faithfulness, answer_relevancy
from .models import EvalItem

def build_generation_eval_items(
    eval_items: List[EvalItem],
    rag_answer_fn: Callable[[str], tuple[str, List[Any]]],
):
    """
    rag_answer_fn(query) -> (answer_text, retrieved_docs)

    retrieved_docs are the same Document objects you use in RAG.
    """
    data = []

    for item in eval_items:
        answer_text, retrieved_docs = rag_answer_fn(item.query)
        contexts = [d.page_content for d in retrieved_docs]

        data.append(
            {
                "question": item.query,
                "answer": answer_text,
                "contexts": contexts,
                "ground_truth": item.ground_truth_answer,
            }
        )

    return data




def evaluate_generation(gen_items: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    gen_items: list of dicts:
      - question
      - answer
      - contexts (list[str])
      - ground_truth
    Returns a dict of metric_name -> score.
    """
    hf_dataset = Dataset.from_list(gen_items)

    result = evaluate(
        hf_dataset,
        metrics=[context_precision, context_recall, faithfulness, answer_relevancy],
    )

    # result.scores is a dict: {"faithfulness": ..., "context_precision": ...}
    return result.scores