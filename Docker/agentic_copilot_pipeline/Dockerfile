FROM ghcr.io/astral-sh/uv:0.6.14-python3.10-bookworm

WORKDIR /app

# System deps (adjust if you don't need all of them)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libjpeg-dev \
    libavif-dev \
    pkg-config \
    curl \
    unzip \
    zip \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry and make it available
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"

# Copy dependency files first (better caching)
COPY pyproject.toml poetry.lock* /app/

# Install deps into the container environment (no venv)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy application code
COPY src/ /app/src

# Copy Alembic config (make sure the destination dir exists in your repo structure)
COPY docker/agentic_copilot_pipeline/alembic.example.ini \
  /app/src/models/db_schemes/lichtblick/alembic.ini

# Entrypoint
COPY docker/agentic_copilot_pipeline/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
