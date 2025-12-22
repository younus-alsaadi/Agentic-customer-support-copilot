from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os

import sys
from pathlib import Path

# Find project root by climbing up from env.py
BASE_DIR = Path(__file__).resolve().parents[5]
sys.path.append(str(BASE_DIR))

print(f"[alembic] Added to path: {BASE_DIR}")

import sys
sys.path.append("/app")

from src.models.db_schemes.lichtblick.schemes import SQLAlchemyBase

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.



config = context.config


# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# Build DB URL from environment variables (K8s Secret / ConfigMap or docker-compose .env)
db_user = os.getenv("POSTGRES_USERNAME", "postgres")
db_password = os.getenv("POSTGRES_PASSWORD", "lichtblick")
db_host = os.getenv("POSTGRES_HOST", "localhost")
db_port = os.getenv("POSTGRES_PORT", "5400")
db_name = os.getenv("POSTGRES_MAIN_DATABASE", "lichtblick")

db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Override sqlalchemy.url from alembic.ini with our env-based URL
config.set_main_option("sqlalchemy.url", db_url)

target_metadata = SQLAlchemyBase.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
