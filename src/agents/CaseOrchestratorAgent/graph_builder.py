from langgraph.graph import StateGraph, END

from langchain_community.chat_models import ChatOpenAI


from src.agents.CaseOrchestratorAgent.CaseState import State
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


def llm_node(state: State) -> State:
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3,api_key=get_settings().OPENAI_API_KEY)

    # pass the conversation to the model
    resp = llm.invoke(state["messages"])

    # append assistant message
    state["messages"].append({"role": "assistant", "content": resp.content})
    return state



def build_graph():
    g = StateGraph(State)

    g.add_node("llm", llm_node)


    g.set_entry_point("llm")

    g.add_edge("llm", END)
    return g.compile()


if __name__ == "__main__":
    s = get_settings()

    graph = build_graph()

    user_text = input("You: ").strip()
    out = graph.invoke({"messages": [{"role": "user", "content": user_text}]})

    print("\nAssistant:", out["messages"][-1]["content"])