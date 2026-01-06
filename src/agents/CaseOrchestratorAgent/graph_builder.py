import asyncio

from langgraph.graph import StateGraph, END

from src.agents.CaseOrchestratorAgent.AgentState import AgentState
from src.agents.CaseOrchestratorAgent.nodes import (
    create_case_node,
    create_msg_node,
    extract_intents_entities_node,
    save_extraction_node,
    auth_policy_evaluator_node,
    review_finalize_node,
    human_review_node,
    auth_session_manager_node,
    create_or_update_auth_request_draft_node,
    approve_and_send_auth_request_node,
    plan_non_auth_actions_node,
    plan_auth_actions_node,
    join_plans_node
)
from src.agents.CaseOrchestratorAgent.routers.route_after_actions_join import route_after_actions_join
from src.agents.CaseOrchestratorAgent.routers.route_auth_branch import route_auth_branch, route_non_auth_branch
from src.agents.CaseOrchestratorAgent.routers.route_after_auth import route_after_auth

from src.helpers.config import get_settings

from dotenv import load_dotenv
load_dotenv()

import os

s = get_settings()

# your settings currently use LANGCHAIN_* names
if s.LANGCHAIN_API_KEY:
    os.environ["LANGSMITH_TRACING"] = "true" if s.LANGCHAIN_TRACING_V2 else "false"
    os.environ["LANGSMITH_API_KEY"] = s.LANGCHAIN_API_KEY
    os.environ["LANGSMITH_PROJECT"] = s.LANGCHAIN_PROJECT or "default"
    if s.LANGCHAIN_ENDPOINT:
        os.environ["LANGSMITH_ENDPOINT"] = s.LANGCHAIN_ENDPOINT


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("extract_intents_entities_node", extract_intents_entities_node)
    g.add_node("create_case_node", create_case_node)
    g.add_node("message_writer_node", create_msg_node)
    g.add_node("save_extraction_node", save_extraction_node)

    g.add_node("auth_policy_evaluator_node", auth_policy_evaluator_node)

    g.add_node("plan_non_auth_actions_node", plan_non_auth_actions_node)

    g.add_node("auth_session_manager_node", auth_session_manager_node)
    g.add_node("plan_auth_actions_node", plan_auth_actions_node)

    g.add_node("join_plans_node", join_plans_node, defer=True)

    g.add_node("human_review_node", human_review_node)

    g.add_node("create_or_update_auth_request_draft_node", create_or_update_auth_request_draft_node)

    g.add_node("approve_and_send_auth_request_node", approve_and_send_auth_request_node)

    g.add_node("review_finalize_node", review_finalize_node)

    # ===== Entry =====
    g.set_entry_point("extract_intents_entities_node")

    # ===== Linear pre-processing =====
    g.add_edge("extract_intents_entities_node", "create_case_node")
    g.add_edge("create_case_node", "message_writer_node")
    g.add_edge("message_writer_node", "save_extraction_node")
    g.add_edge("save_extraction_node", "auth_policy_evaluator_node")

    # ===== Fan-out =====
    # Always plan non-auth

    # In parallel, decide auth branch
    g.add_conditional_edges(
        "auth_policy_evaluator_node",
        route_non_auth_branch,
        {
            "plan_non_auth_actions_node": "plan_non_auth_actions_node",
             END: END,
        },
    )

    # In parallel, decide auth branch
    g.add_conditional_edges(
        "auth_policy_evaluator_node",
        route_auth_branch,
        {
            "auth_session_manager_node": "auth_session_manager_node",
             END: END,
        },
    )

    # ===== Auth flow =====
    g.add_conditional_edges(
        "auth_session_manager_node",
        route_after_auth, # success vs missing
        {
            "plan_auth_actions_node": "plan_auth_actions_node",
            "create_or_update_auth_request_draft_node": "create_or_update_auth_request_draft_node",
        },
    )


    # IMPORTANT: auth request draft must also rejoin
    g.add_edge("create_or_update_auth_request_draft_node", "approve_and_send_auth_request_node")

    g.add_edge("plan_auth_actions_node", "join_plans_node")

    g.add_edge("approve_and_send_auth_request_node", "join_plans_node")

    # ===== Fan-in =====
    # Non-auth branch joins too
    g.add_edge("plan_non_auth_actions_node", "join_plans_node")



    # ===== Review & finalize =====
    g.add_conditional_edges(
        "join_plans_node",
        route_after_actions_join,
        {
            "go_review": "human_review_node",
            END: END,
        },
    )
    g.add_edge("human_review_node", "review_finalize_node")

    g.add_edge("review_finalize_node", END)


    return g.compile()


async def main():
    graph = build_graph()

    email = {
        "from_email": "younis.eng.software@gmail.com",
        "to_email": "test@younus-alsaadi.de",
        "subject": "Meter reading + dynamic tariff question",
        "direction": "inbound",
        "body": """Hello,
         I'd like to submit my latest electricity meter reading and also ask about your dynamic tariff.

        - Meter number: LB-9876543
        - Reading date: 25.09.2025
        - Reading value: 2438 kWh
    
        Questions:
        1) How does your dynamic tariff work?
        2) Would it make sense for a 2-person household with an induction stove and no EV?
        3) Do prices change hourly?
        4) Can I switch any time?
    
        I can't find my contract number right now — if you need it, please tell me what I should provide.
    
        Thanks a lot,
        Jon Candy
        """,
    }

    email_no_auth = {
        "from_email": "younis.eng.software@gmail.com",
        "to_email": "test@younus-alsaadi.de",
        "subject": "Meter reading + dynamic tariff question",
        "direction": "inbound",
        "body": """
            Can you explain the dynamic tariff?
            """,
    }


    email_reply = {
        "from_email": "younis.eng.software@gmail.com",
        "to_email": "test@younus-alsaadi.de",
        "subject": "Meter reading + dynamic tariff question",
        "direction": "inbound",
        "body": """,
        Hello,

        
        Contract number = C-001
        My postal number, is 22201
        
        
        Best regards
        Younus AL-Saadi
        
        On Tue, 30 Dec 2025 at 18:11, <test@younus-alsaadi.de> wrote:
        Postal code,
        
        I am the AI customer support assistant handling your case. To proceed with your request, we kindly ask you to provide the following information to verify your identity:
        - Contract number
        
        Please reply to this email with the requested details and ensure the case ID a96b72b9-f2ff-4660-a00e-7686eb843cc3 remains in the subject line.

        Thank you for your cooperation.

        Best regards,
        Customer Support Team
        """,
    }

    initial_state: AgentState = {
        "Message": email
        ,
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




