import json
from typing import List
import asyncio
from .models import EvalItem
from .generation_eval import build_generation_eval_items, evaluate_generation
from .push_metrics import push_retrieval_metrics, push_generation_metrics
from ..utils.client_deps_container import DependencyContainer


def load_eval_items(path: str) -> List[EvalItem]:
    items:List[EvalItem]=[]

    with open(path,"r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            items.append(
                EvalItem(
                    query=obj["query"],
                    ground_truth_answer=obj["ground_truth_answer"],
                    ground_truth_doc_ids=obj["ground_truth_doc_ids"],

            ))

    return items

async def build_nlp_controller() -> NLPController:
    container = await DependencyContainer.create()
    # keep container so you can shut it down later if you want
    # but for a short script it's often ok to let process exit

    return NLPController(
        vectordb_client=container.vectordb_client,
        generation_client=container.generation_client,
        embedding_model_client=container.embedding_client,
        template_parser=container.template_parser,
    )

async def rag_retrieve_async(nlp: NLPController, project: Project, query: str, k: int):
    # use your existing search_vector_db_collection
    results = await nlp.search_vector_db_collection(
        project=project,
        text=query,
        limit=k,
    )
    return results


async def rag_answer_async(nlp: NLPController, project: Project, query: str):
    answer, full_prompt, chat_history = await nlp.answer_rag_question(
        project=project,
        query=query,
        limit=10,
    )
    # answer_from_generation_model is probably a dict/obj in your code,
    # adapt to get plain string + retrieved docs
    return answer["answer_text"], answer["retrieved_docs"]

def make_rag_functions(nlp: NLPController, project: Project):
    def rag_retrieve(query: str, k: int):
        return asyncio.run(rag_retrieve_async(nlp, project, query, k))

    def rag_answer(query: str):
        return asyncio.run(rag_answer_async(nlp, project, query))

    return rag_retrieve, rag_answer



def main():
    eval_items = load_eval_items("eval/intents_entities_eval_dataset.jsonl")

    # build deps + controller
    nlp = asyncio.run(build_nlp_controller())
    # load project from DB or create a dummy one
    project = Project(project_id="eval_project")

    rag_retrieve, rag_answer = make_rag_functions(nlp, project)

    # retrieval eval
    retrieval_results, avg_retrieval_metrics = evaluate_retrieval(
        eval_items,
        rag_retrieve,
    )
    print("Retrieval metrics per query:")
    for r in retrieval_results:
        print(r)
    print("Average retrieval metrics:", avg_retrieval_metrics)
    push_retrieval_metrics(avg_retrieval_metrics)

    # generation eval
    gen_items = build_generation_eval_items(eval_items, rag_answer)
    gen_scores = evaluate_generation(gen_items)
    print("Generation metrics:", gen_scores)
    push_generation_metrics(gen_scores)



if __name__ == "__main__":
    main()