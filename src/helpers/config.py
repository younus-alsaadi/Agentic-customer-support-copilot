from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import List, Optional

THIS_DIR = Path(__file__).resolve().parent      # .../src/helpers
ENV_PATH = THIS_DIR.parent / ".env"        # .../project_root/.env


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str

    FILE_ALLOWED_TYPES: str
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int

    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str




    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str

    OPENAI_API_KEY: str = None
    OPENAI_API_URL: Optional[str] = None
    COHERE_API_KEY: str = None

    GENERATION_MODEL_ID_LITERAL: Optional[List[str]] = None
    GENERATION_MODEL_ID: str = None
    EMBEDDING_MODEL_ID: str = None
    EMBEDDING_MODEL_SIZE: int = None
    INPUT_DAFAULT_MAX_CHARACTERS: int = None
    GENERATION_DAFAULT_MAX_TOKENS: int = None
    GENERATION_DAFAULT_TEMPERATURE: float = None

    AZURE_OPENAI_API_KEY: str = None
    AZURE_OPENAI_ENDPOINT : str = None
    AZURE_OPENAI_API_VERSION : str = None
    AZURE_OPENAI_CHAT_DEPLOYMENT : str = None
    AZURE_OPENAI_EMBED_DEPLOYMENT : str = None
    AZURE_OPENAI_EMBED_DIMENSIONS : str = None

    LANGCHAIN_TRACING_V2:str = None
    LANGCHAIN_ENDPOINT:str = None
    LANGCHAIN_API_KEY:str = None
    LANGCHAIN_PROJECT:str= None

    VECTOR_DB_BACKEND_LITERAL: Optional[List[str]] = None
    VECTOR_DB_BACKEND : str
    VECTOR_DB_PATH : str
    VECTOR_DB_DISTANCE_METHOD: str = None
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int = 100

    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    PII_HASH_SALT : str

    REQUIRED_FIELDS_FOR_VERIFICATION:List[str]
    SENSITIVE_INTENTS:List[str]

    EMAIL_USER : str
    EMAIL_PASS : str

    IMAP_HOST : str
    IMAP_PORT : int

    SMTP_HOST : str
    SMTP_PORT : int
    SMTP_STARTTLS : int
    SMTP_SSL:int

    model_config = SettingsConfigDict(env_file=str(ENV_PATH), extra="ignore")




def get_settings() -> Settings:
    return Settings()

