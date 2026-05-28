from __future__ import annotations

from pathlib import Path
import json
import tempfile
from unittest import mock

from system.application.health_service import database_source_label, mask_database_url
from system.infrastructure.config import database_backend
from system.infrastructure.persistence.connection import database_backend_for_target, is_database_url, to_percent_sql
from system.infrastructure.persistence.dialect import ddl_filename, mysql_index_statement
from system.infrastructure.persistence.readiness import clear_readiness, is_ready, mark_ready


class DummyConnection:
    def __init__(self, backend: str, database_identity: str = "") -> None:
        self.backend = backend
        self.database_identity = database_identity


def test_database_backend_for_target_recognizes_supported_urls() -> None:
    assert database_backend_for_target("postgresql://user:pass@example/db") == "postgres"
    assert database_backend_for_target("postgres://user:pass@example/db") == "postgres"
    assert database_backend_for_target("mysql://user:pass@example/db") == "mysql"
    assert database_backend_for_target("mysql+pymysql://user:pass@example/db") == "mysql"
    assert database_backend_for_target(Path("ops_admin.db")) == "sqlite"


def test_database_backend_reads_application_backend_without_url() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "application.json"
        config_path.write_text(json.dumps({"database": {"backend": "mysql"}}), encoding="utf-8")

        with mock.patch.dict(
            "os.environ",
            {
                "OPS_ADMIN_APPLICATION_CONFIG": str(config_path),
                "FG_AGENT_DATABASE_CONFIG": "",
                "FG_AGENT_DATABASE_URL": "",
                "SUPABASE_DB_URL": "",
                "DATABASE_URL": "",
            },
            clear=False,
        ):
            assert database_backend() == "mysql"


def test_is_database_url_includes_mysql() -> None:
    assert is_database_url("mysql://user:pass@example/db")
    assert is_database_url("postgresql://user:pass@example/db")
    assert not is_database_url("ops_admin.db")


def test_percent_sql_converter_preserves_existing_shape() -> None:
    assert to_percent_sql("SELECT * FROM users WHERE id = ? AND name = ?") == "SELECT * FROM users WHERE id = %s AND name = %s"


def test_ddl_filename_uses_connection_backend() -> None:
    assert ddl_filename(DummyConnection("mysql")) == "ddl.mysql.sql"
    assert ddl_filename(DummyConnection("postgres")) == "ddl.postgres.sql"


def test_mysql_index_statement_removes_if_not_exists() -> None:
    assert (
        mysql_index_statement("CREATE UNIQUE INDEX IF NOT EXISTS idx_users ON users(username)")
        == "CREATE UNIQUE INDEX idx_users ON users(username)"
    )
    assert (
        mysql_index_statement("CREATE INDEX IF NOT EXISTS idx_users ON users(username)")
        == "CREATE INDEX idx_users ON users(username)"
    )


def test_health_helpers_label_and_mask_mysql_urls() -> None:
    assert database_source_label("mysql") == "MySQL"
    assert mask_database_url("mysql://root:secret@example:3306/ops_admin") == "mysql://***@example:3306/ops_admin"


def test_schema_readiness_is_scoped_to_database_identity() -> None:
    clear_readiness()
    first = DummyConnection("mysql", "db-host-1:3306/ops_admin")
    second = DummyConnection("mysql", "db-host-2:3306/ops_admin")

    mark_ready(first, "appearance")

    assert is_ready(first, "appearance")
    assert not is_ready(second, "appearance")
