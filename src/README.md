# Agentic customer support-copilot



## Requirements

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

### Install the required packages

```bash
$ pip install -r requirements.txt
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
