APP_NAME="LichtBlick_case_study"
APP_VERSION="0.1"

=
FILE_ALLOWED_TYPES=["email"]

FILE_MAX_SIZE=10
FILE_DEFAULT_CHUNK_SIZE=512000 # 512KB

=
POSTGRES_USERNAME="postgres"
POSTGRES_PASSWORD="lichtblick_us"
POSTGRES_HOST="localhost"
POSTGRES_PORT=5432
POSTGRES_MAIN_DATABASE="lichtblick"

=
# ========================= LLM Config =========================
GENERATION_BACKEND = "OPENAI"
EMBEDDING_BACKEND = "COHERE"

=
OPENAI_API_KEY="sk-"
OPENAI_API_URL=
COHERE_API_KEY="m8-"

=
GENERATION_MODEL_ID_LITERAL = ["gpt-4o-mini", "gpt-4o"]
GENERATION_MODEL_ID="gpt-4o-mini"
EMBEDDING_MODEL_ID="embed-multilingual-v3.0"
EMBEDDING_MODEL_SIZE=384

=
INPUT_DAFAULT_MAX_CHARACTERS=1024
GENERATION_DAFAULT_MAX_TOKENS=200
GENERATION_DAFAULT_TEMPERATURE=0.1

LANGCHAIN_TRACING_V2="true"
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY=""
LANGCHAIN_PROJECT="Agentic-customer-support-copilot"


# =========================
# Azure OpenAI (Cloud)
# =========================
AZURE_OPENAI_API_KEY=""
AZURE_OPENAI_ENDPOINT=""
AZURE_OPENAI_API_VERSION="2024-02-15-preview"

# Deployments
AZURE_OPENAI_CHAT_DEPLOYMENT=""
AZURE_OPENAI_EMBED_DEPLOYMENT=""


=
# ========================= Vector DB Config =========================
VECTOR_DB_BACKEND_LITERAL = ["QDRANT", "PGVECTOR"]
VECTOR_DB_BACKEND = "PGVECTOR"
VECTOR_DB_PATH = "qdrant_db"
VECTOR_DB_DISTANCE_METHOD = "cosine"
VECTOR_DB_PGVEC_INDEX_THRESHOLD =

=
# ========================= Template Configs =========================
PRIMARY_LANG = "De"
DEFAULT_LANG = "en"

PII_HASH_SALT=""

REQUIRED_FIELDS_FOR_VERIFICATION=["contract_number","birthdate","postal_code"]

SENSITIVE_INTENTS=["MeterReadingSubmission","MeterReadingCorrection","PersonalDataChange","ContractIssue"]


#============ IMAP/SMTP Server ================#

EMAIL_USER=""
EMAIL_PASS=""

IMAP_HOST=""
IMAP_PORT=993

SMTP_HOST=""
SMTP_PORT=465
SMTP_STARTTLS=0
SMTP_SSL=1