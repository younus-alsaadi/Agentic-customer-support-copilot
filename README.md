# Agentic customer support-copilot


This project is an agentic customer support copilot for handling customer emails end-to-end.

It works like  “support teammate”:

* Reads an inbound email and creates (or re-uses) a Case

* Saves inbound/outbound emails in Messages

* Uses an LLM to extract intents + entities (stored in Extractions)

* If the request is sensitive, it triggers an auth gate (stored in AuthSessions)

* Plans what to do next and creates a reply draft (stored in Drafts)

* Runs a human-in-the-loop review step (stored in Reviews)

* Creates actions (stored in Actions)
* Sends the final email (using LLM + MCP server)

```
Inbound Email
   ↓
Case Resolver  →  Messages (inbound)
   ↓
LLM Extraction →  Extractions
   ↓
Auth Gate (optional) → AuthSessions
   ↓
Draft Reply + Action Plan → Drafts
   ↓
Human Review → Reviews
   ↓
MCP Tools Execution:
   - Send email (SMTP) + LLM
   ↓
Messages (outbound) + Actions
```

### Supported LLM providers

This project is LLM-provider agnostic: the agent logic stays the same, and you can plug in different LLM backends by changing configuration.

It can run with:

* OpenAI (cloud)
* Azure OpenAI (cloud)
* Cohere (cloud)
* Hugging Face
* Ollama (local)

***

## Test the model form Langsimth:
* [Example 1 ]()
* [Example 2]()
* [Example 3]() 

# Installation:

### Requirements

- Python 3.12 or later

### Install Python using MiniConda

1. Download and install MiniConda from [here](https://docs.anaconda.com/free/miniconda/#quick-command-line-install)
2. Create a new environment:
   ```bash
   conda create -n rag_system python=3.12
3) Activate the environment:
    ```bash
    $ conda activate mini-rag
   
## Installation

### Install the required dependencies

This project uses [Poetry](https://python-poetry.org/) for dependency management and virtual environments.

1) To install all required packages, run:

```bash
# Install dependencies from pyproject.toml
poetry install
```

2) If this is your first time using Poetry, you can install it with:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3) In your project root (where pyproject.toml is)
```bash
cd /path/to/your/project
```
4) Tell Poetry to use the current Python (from the conda env)
```
poetry env use "$(which python)"
```

5) Install dependencies
```
poetry install
```


## Run Docker Compose Services

```bash
$ cd docker
$ cp .env.example .env
```

- update `.env` with your credentials



```bash
$ cd docker
$ sudo docker compose up -d
```

## Install Run Alembic Migrations to install DB sechma in PGSQL

### Configuration

```bash
cp alembic.ini.example alembic.ini
```
Update alembic.ini → sqlalchemy.url with your PostgreSQL credentials.

Example format:
```
postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME
```

- Update the `alembic.ini` with your database credentials (`sqlalchemy.url`)

### (Optional) Create a new migration

```bash
alembic revision --autogenerate -m "Add ..."
```

### Upgrade the database

```bash
alembic upgrade head
```