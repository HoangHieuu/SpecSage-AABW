from datetime import UTC, datetime

from pc_build_copilot import catalog_repository, postgres_catalog
from pc_build_copilot.catalog_models import CatalogSnapshot, ComponentCategory
from pc_build_copilot.catalog_repository import CatalogRepository
from pc_build_copilot.catalog_validation import validate_catalog

from test_catalog_ingestion import _items


SNAPSHOT_AT = datetime(2026, 6, 27, tzinfo=UTC)


class FakePostgresCatalogRepository:
    def __init__(self, database_url: str, *, fallback: CatalogRepository) -> None:
        self.database_url = database_url
        self.fallback = fallback


def test_catalog_repository_factory_uses_postgres_when_url_is_configured(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/catalog")
    monkeypatch.setattr(
        postgres_catalog,
        "PostgresCatalogRepository",
        FakePostgresCatalogRepository,
    )

    repository = catalog_repository.create_catalog_repository()

    assert isinstance(repository, FakePostgresCatalogRepository)
    assert repository.database_url == "postgresql://example/catalog"
    assert isinstance(repository.fallback, CatalogRepository)


def test_catalog_repository_factory_can_force_json_fallback(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/catalog")
    monkeypatch.setenv("PC_BUILD_COPILOT_CATALOG_STORE", "json")

    repository = catalog_repository.create_catalog_repository()

    assert isinstance(repository, CatalogRepository)


def test_postgres_catalog_schema_matches_versioned_catalog_contract() -> None:
    schema = "\n".join(postgres_catalog.POSTGRES_CATALOG_SCHEMA_STATEMENTS)

    assert "catalog_versions" in schema
    assert "catalog_skus" in schema
    assert "payload_json JSONB NOT NULL" in schema
    assert "validation_json JSONB NOT NULL" in schema
    assert "idx_catalog_versions_single_active" in schema
    assert "idx_catalog_skus_snapshot_category_price" in schema
    assert "idx_catalog_skus_specs_gin" in schema
    assert "TIMESTAMPTZ NOT NULL" in schema


def test_loaded_catalog_snapshot_is_revalidated_before_insert(monkeypatch) -> None:
    captured: list[tuple[str, CatalogSnapshot]] = []
    snapshot = CatalogSnapshot(
        snapshot_version="catalog_test_postgres",
        generated_at=SNAPSHOT_AT,
        source="test_fixture",
        items=_items(),
        validation=None,
    )

    def fake_ensure_catalog_schema(database_url: str) -> None:
        assert database_url == "postgresql://example/catalog"

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=None):
            captured.append(("execute", snapshot))
            return self

        def cursor(self):
            return self

        def executemany(self, sql, params):
            captured.append(("executemany", snapshot))

    monkeypatch.setattr(postgres_catalog, "ensure_catalog_schema", fake_ensure_catalog_schema)
    monkeypatch.setattr(
        postgres_catalog,
        "_connect",
        lambda database_url: FakeConnection(),
    )

    loaded = postgres_catalog.load_catalog_snapshot(
        "postgresql://example/catalog",
        snapshot,
    )

    expected = validate_catalog(
        snapshot.items,
        snapshot_version=snapshot.snapshot_version,
        generated_at=snapshot.generated_at,
    )
    assert loaded.validation is not None
    assert loaded.validation.snapshot_version == expected.snapshot_version
    assert loaded.validation.generated_at == expected.generated_at
    assert loaded.validation.sku_count == expected.sku_count
    assert loaded.validation.blocking_issue_count == expected.blocking_issue_count
    assert loaded.validation.production_gap_categories == expected.production_gap_categories
    assert any(kind == "executemany" for kind, _ in captured)


def test_postgres_catalog_query_uses_active_version_and_returns_payloads(
    monkeypatch,
) -> None:
    items = _items()
    gpu = next(item for item in items if item.category == ComponentCategory.VGA)
    captured: list[tuple[str, object]] = []

    def fake_ensure_catalog_schema(database_url: str) -> None:
        assert database_url == "postgresql://example/catalog"

    class FakeResult:
        def __init__(self, *, one=None, rows=None):
            self.one = one
            self.rows = rows or []

        def fetchone(self):
            return self.one

        def fetchall(self):
            return self.rows

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=None):
            captured.append((sql, params))
            if "SELECT snapshot_version, generated_at" in sql:
                return FakeResult(
                    one={
                        "snapshot_version": "catalog_test_postgres",
                        "generated_at": SNAPSHOT_AT,
                    }
                )
            return FakeResult(
                rows=[{"payload_json": gpu.model_dump(mode="json")}]
            )

    monkeypatch.setattr(postgres_catalog, "ensure_catalog_schema", fake_ensure_catalog_schema)
    monkeypatch.setattr(
        postgres_catalog,
        "_connect",
        lambda database_url: FakeConnection(),
    )

    repository = postgres_catalog.PostgresCatalogRepository(
        "postgresql://example/catalog"
    )
    response = repository.query(
        category=ComponentCategory.VGA,
        in_stock=True,
        min_vram_gb=8,
    )

    assert response.snapshot_version == "catalog_test_postgres"
    assert response.catalog_snapshot_at == SNAPSHOT_AT
    assert response.sku_count == 1
    assert response.items[0].sku == gpu.sku
    query_sql, query_params = captured[-1]
    assert "FROM catalog_skus" in query_sql
    assert "stock_quantity > 0" in query_sql
    assert "vram_gb" in query_sql
    assert query_params == ["catalog_test_postgres", "vga", 8]
