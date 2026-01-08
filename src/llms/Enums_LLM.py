from dataclasses import dataclass
from enum import Enum

class Enums_LLM(Enum):
    OPENAI = "OPENAI"
    COHERE = "COHERE"
    AZUREOPENAI = "AZUREOPENAI"
    HF = "HF"

class OpenAIEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class CoHereEnums(Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "CHATBOT"

    DOCUMENT = "search_document"
    QUERY = "search_query"


@dataclass(frozen=True)
class HFEnums:
    SYSTEM: str = "system"
    USER: str = "user"
    ASSISTANT: str = "assistant"


class DocumentTypeEnum(Enum):
    DOCUMENT = "document"
    QUERY = "query"