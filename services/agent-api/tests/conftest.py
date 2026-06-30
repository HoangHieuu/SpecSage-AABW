import pytest

from pc_build_copilot.persistence import POSTGRES_URL_ENV_CANDIDATES


@pytest.fixture(autouse=True)
def clear_production_database_urls(monkeypatch):
    for env_key in POSTGRES_URL_ENV_CANDIDATES:
        monkeypatch.delenv(env_key, raising=False)
