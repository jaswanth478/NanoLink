from __future__ import annotations


import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
)

from dotenv import load_dotenv
load_dotenv()

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy import create_engine
from alembic import context

from config.settings import get_settings
from app.db import models

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

settings = get_settings()
# Convert async URL to sync URL for Alembic (migrations need sync driver)
db_url = settings.database_url
if db_url.startswith("postgresql+asyncpg://"):
    # Replace asyncpg with psycopg (sync driver) and convert sslmode to ssl parameter
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    # Remove sslmode from URL - psycopg handles SSL via connection args
    if "?sslmode=require" in db_url:
        db_url = db_url.replace("?sslmode=require", "")
        # SSL will be enabled via connect_args in create_engine

config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = models.Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # For sync migrations, use psycopg and handle SSL via connect_args
    connect_args = {}
    if settings.database_url and "sslmode=require" in settings.database_url:
        connect_args["sslmode"] = "require"
    
    connectable = create_engine(db_url, poolclass=pool.NullPool, connect_args=connect_args)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


def run_migrations() -> None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()


run_migrations()
