from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from audit_logging.application import dispatcher, services
from audit_logging.infrastructure.persistence import repositories
from audit_logging.infrastructure.persistence.bootstrap import ensure_audit_logging_schema
from system.application.tenancy import reset_tenant_scope, set_tenant_scope
from system.application.database import connect
from system.domain.tenancy import TenantScope
from system.infrastructure.persistence.connection import configure_sql_observer


class AuditLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "audit.db"
        self.env_patch = mock.patch.dict(
            "os.environ",
            {
                "FG_AGENT_DATABASE_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-database.json"),
                "FG_AGENT_DATABASE_URL": "",
                "SUPABASE_DB_URL": "",
                "DATABASE_URL": "",
                "FG_AGENT_DB_PATH": str(self.db_path),
            },
            clear=False,
        )
        self.env_patch.start()
        dispatcher.reset_for_tests()
        dispatcher.configure_repository(repositories)
        self.initialize_db()

    def tearDown(self) -> None:
        dispatcher.stop_worker()
        dispatcher.stop_worker()
        dispatcher.flush_now()
        configure_sql_observer(None)
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def initialize_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_audit_logging_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def test_async_api_log_flushes_to_database(self) -> None:
        dispatcher.start_worker()
        accepted = dispatcher.record_api_log(
            {
                "tenant_id": 7,
                "event_action": "GET /api/example",
                "request_method": "GET",
                "request_path": "/api/example",
                "status_code": 200,
                "duration_ms": 12,
                "summary": "GET /api/example -> 200",
            }
        )
        self.assertTrue(accepted)

        dispatcher.stop_worker()
        dispatcher.stop_worker()
        dispatcher.flush_now()

        response = services.list_logs(
            category="api",
            page=1,
            page_size=20,
            current_user={"id": 10, "tenant_id": 7, "current_tenant": {"id": 7}},
        )
        self.assertEqual(response["pagination"]["total"], 1)
        self.assertEqual(response["items"][0]["request_path"], "/api/example")

    def test_sql_observer_records_error_sql_without_params(self) -> None:
        dispatcher.start_worker()
        dispatcher.observe_sql(
            sql="SELECT * FROM users WHERE password = ? AND id = 123",
            params=("secret",),
            duration_ms=3,
            success=False,
            error_message="boom",
            backend="sqlite",
            readonly=True,
        )
        dispatcher.stop_worker()
        dispatcher.flush_now()

        response = services.list_logs(
            category="sql",
            page=1,
            page_size=20,
            current_user={"id": 10, "tenant_id": 0, "current_tenant": {"id": 0}, "is_platform_admin": True},
        )
        self.assertEqual(response["pagination"]["total"], 1)
        item = response["items"][0]
        self.assertEqual(item["event_outcome"], "failed")
        self.assertNotIn("secret", item["sql_template"])
        self.assertIn("id = ?", item["sql_template"])

    def test_sql_observer_uses_current_tenant_scope(self) -> None:
        dispatcher.start_worker()
        token = set_tenant_scope(
            TenantScope(
                tenant_id=7,
                tenant_key="default",
                tenant_name="Default Tenant",
                is_platform_admin=False,
                principal_id=10,
                principal_name="tenant-admin",
            )
        )
        try:
            dispatcher.observe_sql(
                sql="SELECT * FROM orders WHERE id = 123",
                params=(),
                duration_ms=3,
                success=False,
                error_message="boom",
                backend="sqlite",
                readonly=True,
            )
        finally:
            reset_tenant_scope(token)
        dispatcher.stop_worker()
        dispatcher.flush_now()

        response = services.list_logs(
            category="sql",
            page=1,
            page_size=20,
            current_user={"id": 10, "tenant_id": 7, "current_tenant": {"id": 7}},
        )
        self.assertEqual(response["pagination"]["total"], 1)
        self.assertEqual(response["items"][0]["tenant_id"], 7)

    def test_logs_without_explicit_tenant_use_current_tenant_scope(self) -> None:
        dispatcher.start_worker()
        token = set_tenant_scope(
            TenantScope(
                tenant_id=9,
                tenant_key="tenant-nine",
                tenant_name="Tenant Nine",
                is_platform_admin=False,
                principal_id=20,
                principal_name="operator",
            )
        )
        try:
            accepted = dispatcher.enqueue_log(
                "operation",
                {
                    "event_action": "demo.update",
                    "event_outcome": "success",
                    "summary": "demo update",
                },
            )
        finally:
            reset_tenant_scope(token)
        self.assertTrue(accepted)

        dispatcher.stop_worker()
        dispatcher.flush_now()

        response = services.list_logs(
            category="operation",
            page=1,
            page_size=20,
            current_user={"id": 20, "tenant_id": 9, "current_tenant": {"id": 9}},
        )
        self.assertEqual(response["pagination"]["total"], 1)
        self.assertEqual(response["items"][0]["tenant_id"], 9)

    def test_explicit_platform_tenant_id_is_preserved(self) -> None:
        dispatcher.start_worker()
        token = set_tenant_scope(
            TenantScope(
                tenant_id=9,
                tenant_key="tenant-nine",
                tenant_name="Tenant Nine",
                is_platform_admin=False,
                principal_id=20,
                principal_name="operator",
            )
        )
        try:
            accepted = dispatcher.enqueue_log(
                "system",
                {
                    "tenant_id": 0,
                    "event_action": "platform.maintenance",
                    "event_outcome": "success",
                    "summary": "platform maintenance",
                },
            )
        finally:
            reset_tenant_scope(token)
        self.assertTrue(accepted)

        dispatcher.stop_worker()
        dispatcher.flush_now()

        response = services.list_logs(
            category="system",
            page=1,
            page_size=20,
            current_user={"id": 1, "tenant_id": 0, "current_tenant": {"id": 0}, "is_platform_admin": True},
        )
        self.assertEqual(response["pagination"]["total"], 1)
        self.assertEqual(response["items"][0]["tenant_id"], 0)

    def test_platform_admin_can_filter_logs_by_tenant(self) -> None:
        repositories.insert_many(
            [
                {
                    "category": "api",
                    "tenant_id": 7,
                    "event_action": "GET /api/a",
                    "request_method": "GET",
                    "request_path": "/api/a",
                    "status_code": 200,
                    "duration_ms": 10,
                    "summary": "tenant 7",
                },
                {
                    "category": "api",
                    "tenant_id": 8,
                    "event_action": "GET /api/b",
                    "request_method": "GET",
                    "request_path": "/api/b",
                    "status_code": 200,
                    "duration_ms": 20,
                    "summary": "tenant 8",
                },
            ],
        )

        user = {"id": 1, "tenant_id": 0, "current_tenant": {"id": 0}, "is_platform_admin": True}
        all_response = services.list_logs(category="api", page=1, page_size=20, current_user=user)
        tenant_response = services.list_logs(category="api", page=1, page_size=20, current_user=user, tenant_id=8)

        self.assertEqual(all_response["pagination"]["total"], 2)
        self.assertEqual(tenant_response["pagination"]["total"], 1)
        self.assertEqual(tenant_response["items"][0]["tenant_id"], 8)

    def test_tenant_user_cannot_override_log_tenant_filter(self) -> None:
        repositories.insert_many(
            [
                {
                    "category": "api",
                    "tenant_id": 7,
                    "event_action": "GET /api/a",
                    "request_method": "GET",
                    "request_path": "/api/a",
                    "status_code": 200,
                    "duration_ms": 10,
                    "summary": "tenant 7",
                },
                {
                    "category": "api",
                    "tenant_id": 8,
                    "event_action": "GET /api/b",
                    "request_method": "GET",
                    "request_path": "/api/b",
                    "status_code": 200,
                    "duration_ms": 20,
                    "summary": "tenant 8",
                },
            ],
        )

        user = {"id": 2, "tenant_id": 7, "current_tenant": {"id": 7}, "is_platform_admin": False}
        response = services.list_logs(category="api", page=1, page_size=20, current_user=user, tenant_id=8)

        self.assertEqual(response["pagination"]["total"], 1)
        self.assertEqual(response["items"][0]["tenant_id"], 7)

    def test_registered_sql_observer_accepts_connection_hook(self) -> None:
        dispatcher.start_worker()
        configure_sql_observer(dispatcher.observe_sql)

        with self.assertRaises(sqlite3.OperationalError):
            with connect(self.db_path, readonly=True) as conn:
                conn.execute("SELECT * FROM missing_table WHERE id = ?", (123,))

        dispatcher.stop_worker()
        dispatcher.flush_now()
        response = services.list_logs(
            category="sql",
            page=1,
            page_size=20,
            current_user={"id": 1, "tenant_id": 0, "current_tenant": {"id": 0}, "is_platform_admin": True},
        )
        self.assertEqual(response["pagination"]["total"], 1)
        self.assertIn("missing_table", response["items"][0]["sql_template"])

    def test_settings_are_platform_mutable(self) -> None:
        user = {"id": 1, "username": "admin", "is_platform_admin": True}
        response = services.save_settings(0, {"slow_sql_threshold_ms": 750, "plaintext_ip_retention_days": 14}, user)
        self.assertEqual(response["item"]["slow_sql_threshold_ms"], 750)
        self.assertEqual(response["item"]["plaintext_ip_retention_days"], 14)


if __name__ == "__main__":
    unittest.main()
