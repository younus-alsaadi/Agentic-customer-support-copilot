import asyncio
from typing import TypedDict, Dict, Any

from fastmcp import Client
from langgraph.graph import StateGraph, END

from langchain_community.chat_models import ChatOpenAI


from src.agents.CaseOrchestratorAgent.CaseState import State
from src.helpers.config import get_settings

from dotenv import load_dotenv
load_dotenv()

import os

s = get_settings()

MCP_URL = "http://127.0.0.1:8000/mcp"

# your settings currently use LANGCHAIN_* names
if s.LANGCHAIN_API_KEY:
    os.environ["LANGSMITH_TRACING"] = str(s.LANGCHAIN_TRACING_V2 or "true")
    os.environ["LANGSMITH_API_KEY"] = s.LANGCHAIN_API_KEY
    os.environ["LANGSMITH_PROJECT"] = s.LANGCHAIN_PROJECT or "default"
    os.environ["OPENAI_API_KEY"] = s.OPENAI_API_KEY
    if s.LANGCHAIN_ENDPOINT:
        os.environ["LANGSMITH_ENDPOINT"] = s.LANGCHAIN_ENDPOINT

class MailState(TypedDict, total=False):
    uid: str
    mailbox: str
    email: Dict[str, Any]
    explanation: str



def _tool_data(result: Any):
    return getattr(result, "data", result)

async def fetch_email_node(state: MailState) -> MailState:
    uid = state["uid"]
    mailbox = state.get("mailbox", "INBOX")

    print("\n[fetch_email_node] start")
    print("[fetch_email_node] uid:", uid, "mailbox:", mailbox)

    async with Client(MCP_URL) as client:
        print("[fetch_email_node] MCP connected ✅")

        r = await client.call_tool("_email_imap_get", {"uid": uid, "mailbox": mailbox})

        print("[fetch_email_node] raw tool return:", r)
        data = _tool_data(r)
        print("[fetch_email_node] parsed tool data:", data)

        state["email"] = data

    print("[fetch_email_node] done ✅")
    return state



async def explain_node(state: MailState) -> MailState:
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)

    email_obj = state.get("email", {})
    sender = email_obj.get("from", "")
    subject = email_obj.get("subject", "")
    body = (email_obj.get("body", "") or "")[:4000]

    prompt = f"""
    Explain what this email is about in simple English.
    
    Return:
    1) One sentence summary
    2) Key points (bullets)
    3) What the sender wants (one line)
    4) Suggested next action (one line)
    
    From: {sender}
    Subject: {subject}
    Body:
    {body}
    """.strip()

    resp = await llm.ainvoke(prompt)
    state["explanation"] = resp.content
    return state

async def mark_seen_node(state: MailState) -> MailState:
    uid = state["uid"]
    mailbox = state.get("mailbox", "INBOX")

    print("\n[mark_seen_node] start")
    print("[mark_seen_node] uid:", uid, "mailbox:", mailbox)

    async with Client(MCP_URL) as client:
        print("[mark_seen_node] MCP connected ✅")

        r = await client.call_tool("_email_imap_mark_seen", {"uid": uid, "mailbox": mailbox})
        print("[mark_seen_node] raw tool return:", r)
        print("[mark_seen_node] parsed tool data:", _tool_data(r))

    print("[mark_seen_node] done ✅")
    return state

def build_mail_graph():
    g = StateGraph(MailState)

    g.add_node("fetch_email", fetch_email_node)
    g.add_node("explain", explain_node)
    g.add_node("mark_seen", mark_seen_node)

    g.set_entry_point("fetch_email")
    g.add_edge("fetch_email", "explain")
    g.add_edge("explain", "mark_seen")
    g.add_edge("mark_seen", END)

    return g.compile()

async def main():
    graph = build_mail_graph()



    async with Client(MCP_URL) as client:
        while True:
            r = await client.call_tool("_email_imap_search", {"mailbox": "INBOX", "criteria": "UNSEEN", "limit": 5})
            uids = getattr(r, "data", r) or []

            for uid in uids:
                out = await graph.ainvoke({"uid": uid, "mailbox": "INBOX"})
                print("\n--- NEW EMAIL ---")
                print("From:", out.get("email", {}).get("from"))
                print("Subject:", out.get("email", {}).get("subject"))
                print("Explanation:\n", out.get("explanation"))

            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
