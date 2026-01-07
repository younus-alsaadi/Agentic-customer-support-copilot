import json
import asyncio
from typing import List

from src.agents.CaseOrchestratorAgent.tools.extract_intents_entities import extract_intents_entities
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container

from .models import EvalItem
from .generation_eval import build_generation_eval_items, evaluate_generation
from .push_metrics import push_generation_metrics


def load_eval_items(path: str) -> List[EvalItem]:
    items: List[EvalItem] = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            obj = json.loads(line)

            # Allow both spellings (your file uses "email_budy")
            email_body = obj.get("email_body") or obj.get("email_budy") or ""
            email_subject = obj.get("email_subject") or ""
            ground_truth_output = obj.get("ground_truth_output")

            items.append(
                EvalItem(
                    email_budy=email_body,
                    email_subject=email_subject,
                    ground_truth_output=ground_truth_output,
                )
            )

    return items


async def _predict(container, from_email: str, subject: str, body: str):
    # IMPORTANT: await it (your node does)
    return await extract_intents_entities(
        container=container,
        from_email=from_email,
        subject=subject,
        body=body,
    )


def make_extract_intents_entities_function(runner: asyncio.Runner, container):

    def predict(
        body: str,
        from_email: str = "test@test.com",
        subject: str = "test email",
    ):
        return runner.run(_predict(container, from_email, subject, body))

    return predict


def main():
    eval_items = load_eval_items("eval/intents_entities_eval_dataset.jsonl")

    with asyncio.Runner() as runner:
        container = runner.run(get_container())

        predict_fn = make_extract_intents_entities_function(runner, container)

        gen_items = build_generation_eval_items(eval_items, predict_fn)
        gen_scores = evaluate_generation(gen_items)

    print("Generation metrics:", gen_scores)
    push_generation_metrics(gen_scores)

if __name__ == "__main__":
    main()
