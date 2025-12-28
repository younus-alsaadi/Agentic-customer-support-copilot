from typing import TypedDict, List, Dict, Any


class State(TypedDict):
    messages: List[Dict[str, Any]]  # OpenAI-style messages
