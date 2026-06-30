from __future__ import annotations

import os

from pc_build_copilot.build_store import BuildStore
from pc_build_copilot.sqlite_store import create_sqlite_stores
from pc_build_copilot.store import SessionStore


POSTGRES_URL_ENV_CANDIDATES = (
    "DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRES_URL_NON_POOLING",
)


def create_persistent_stores() -> tuple[SessionStore, BuildStore]:
    database_url = resolve_postgres_url()
    if database_url:
        return create_postgres_stores(database_url)
    return create_sqlite_stores()


def create_postgres_stores(database_url: str) -> tuple[SessionStore, BuildStore]:
    from pc_build_copilot.postgres_store import create_postgres_stores as factory

    return factory(database_url)


def resolve_postgres_url() -> str | None:
    for env_key in POSTGRES_URL_ENV_CANDIDATES:
        value = os.environ.get(env_key)
        if value and value.strip():
            return value.strip()
    return None
