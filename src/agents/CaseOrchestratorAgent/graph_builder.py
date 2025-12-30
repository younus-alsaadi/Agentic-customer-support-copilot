import asyncio

from langgraph.graph import StateGraph, END

from src.agents.CaseOrchestratorAgent.AgentState import AgentState
from src.agents.CaseOrchestratorAgent.nodes import (
    create_case_node,
    create_msg_node,
    extract_intents_entities_node,
    save_extraction_node,
    auth_policy_evaluator_node,
    plan_actions_node,
    review_finalize_node,
    human_review_node
)
from src.helpers.config import get_settings

from dotenv import load_dotenv
load_dotenv()

import os

s = get_settings()

# your settings currently use LANGCHAIN_* names
if s.LANGCHAIN_API_KEY:
    os.environ["LANGSMITH_TRACING"] = str(s.LANGCHAIN_TRACING_V2 or "true")
    os.environ["LANGSMITH_API_KEY"] = s.LANGCHAIN_API_KEY
    os.environ["LANGSMITH_PROJECT"] = s.LANGCHAIN_PROJECT or "default"
    if s.LANGCHAIN_ENDPOINT:
        os.environ["LANGSMITH_ENDPOINT"] = s.LANGCHAIN_ENDPOINT


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("create_case_node", create_case_node)
    g.add_node("message_writer_node", create_msg_node)
    g.add_node("extract_intents_entities_node", extract_intents_entities_node)
    g.add_node("save_extraction_node", save_extraction_node)
    g.add_node("auth_policy_evaluator_node", auth_policy_evaluator_node)
    g.add_node("plan_actions_node", plan_actions_node)
    g.add_node("human_review_node", human_review_node)
    g.add_node("review_finalize_node", review_finalize_node)

    g.set_entry_point("create_case_node")

    g.add_edge("create_case_node", "message_writer_node")
    g.add_edge("message_writer_node", "extract_intents_entities_node")
    g.add_edge("extract_intents_entities_node", "save_extraction_node")
    g.add_edge("save_extraction_node", "auth_policy_evaluator_node")
    g.add_edge("auth_policy_evaluator_node","plan_actions_node")

    g.add_edge("plan_actions_node", "human_review_node")
    g.add_edge("human_review_node", "review_finalize_node")
    g.add_edge("review_finalize_node", END)

    return g.compile()


async def main():
    graph = build_graph()

    email = {  # <-- NO trailing comma
        "from_email": "younis.eng.software@gmail.com",
        "to_email": "test@younus-alsaadi.de",
        "subject": "Meter reading",
        "body": "Hello, my meter reading is 12345. and Can you explain the dynamic tariff? Younus AL-Saadi",
        "direction": "inbound",
    }

    initial_state: AgentState = {
        "Message": email,
        "errors": [],
    }

    # Run once, return final state
    final_state = await graph.ainvoke(initial_state)

    print("\n=== FINAL STATE ===")
    print(final_state)

    # Helpful: show errors only
    if final_state.get("errors"):
        print("\n=== ERRORS ===")
        for e in final_state["errors"]:
            print(e)


if __name__ == "__main__":
    asyncio.run(main())




