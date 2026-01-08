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

## Workflow

![Agentic Email Copilot Workflow](examples/workflow.png)


### Supported LLM providers

This project is LLM-provider agnostic: the agent logic stays the same, and you can plug in different LLM backends by changing configuration.

It can run with:

* OpenAI (cloud)
* Azure OpenAI (cloud)
* Cohere (cloud)
* Ollama (local)
* Hugging Face (local via Transformers) — tested with `mistralai/Ministral-3B-Instruct`

***
## Test runs (LangSmith traces + email screenshots)

Below are real end-to-end examples. Each one links to a LangSmith trace and includes a screenshot of the generated email.

### Example 1 — Auth required (missing customer info)
- Trace: [LangSmith run](https://smith.langchain.com/public/49c67b42-7b5e-471f-a796-b1a9261bd838/r)
- Output email (screenshot):

![Example 1 email screenshot](examples/example1.png)

---

### Example 2 — Mixed intents (public question + auth-required request, auth succeeds)
- Trace: [LangSmith run](https://smith.langchain.com/public/4f145ab0-75e0-47dd-9d02-e216a6913a9d/r)
- Output email (screenshot):

![Example 2 email screenshot](examples/example2.png)

---

### Example 3 — No auth required (public question only)
- Trace: [LangSmith run](https://smith.langchain.com/public/731a1811-f873-42bf-830a-81891ef5017e/r)
- Output email (screenshot):

![Example 3 email screenshot](examples/example3.png)


---

## Deployment (VM + Kubernetes + Cloud)

This pipeline is ready for deployment in different environments:

- **Dedicated server / Virtual Machine (VM)** using **Docker Compose**
- **Dedicated server / VM** using **Kubernetes** for **container orchestration**
  (self-managed cluster like **microk8s**)
- **Cloud Kubernetes**:
  - **AWS (EKS)**
  - **Azure (AKS)**

It uses:
- **Docker images** to package and ship services
- **Kubernetes** to orchestrate containers (deployments, services, scaling, configs, secrets)
- **IaC (Terraform)** to provision cloud infrastructure (EKS/AKS and related resources)
- **CI/CD (GitHub Actions)** to automate build, push, and deployment workflows

---

---

## Evaluation (LLM output quality)

We evaluate the quality of the LLM-generated responses using **Ragas**.

Ragas helps measure things like:
- answer correctness / faithfulness
- relevance


This is useful to compare:
- different LLM providers (OpenAI, Azure OpenAI, Cohere, HF, Ollama)
- different prompts

---

## Observability & Monitoring (latency, errors, system health)

This project includes monitoring with **Prometheus + Grafana**.

We track:
- **API / agent latency** (request duration, tool duration, end-to-end case duration)
- **Error rate** (failed runs, failed tool calls, exceptions)
- **PostgreSQL metrics** (connections, query performance, DB health)
- **System metrics** via **Node Exporter** (CPU, RAM, disk, network)

This makes it easy to debug slowdowns, failures, and capacity issues.

### Suggested SLIs (future improvement)

In the future, we can add Service Level Indicators (SLIs) to measure reliability and performance:

- **Latency:** p50 / p95 / p99 request duration
- **Error rate:** percentage of requests that fail

### Possible SLOs (future improvement)

Example Service Level Objectives (SLOs) we could define:

- **API p95 latency < 2s**
- **Error rate < 1%**
- **Service availability > 99.9%**

---

## Security & Privacy

- `hash_field` used for hashing sensitive fields.
- `mask_value` used for masking sensitive values in logs and outputs.
- Human-in-the-loop review step included (approve / reject / needs changes) before outbound emails.
- Prompt rules added:
  - minimal required data requested
  - sensitive values not repeated unless required
  - no invented customer data
  - separation of public vs. auth-required intents
- Support for local LLMs included (e.g., Ollama, Hugging Face) for privacy-focused deployments.

---

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

---

## Send emails (MCP server)

To actually send outbound emails, you must run the **MCP mail server**.  
The agent will call MCP tools (for example `email_smtp_send`) to deliver the final message.

Start the MCP server from the project root:

```bash
python -m src.email_servers.IMAPSMTP.imap_smtp_mcp_server
```

## License

This repository is provided for review purposes only. Copying, redistribution, or production use is not permitted. See `LICENSE`.
