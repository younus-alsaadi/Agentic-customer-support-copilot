#!/bin/bash
set -e

echo "Running database migrations..."
cd /app/src/models/db_schemes/rag_qa/
alembic upgrade head
cd /app

exec "$@"