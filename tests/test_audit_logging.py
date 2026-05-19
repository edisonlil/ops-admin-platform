from __future__ import annotations

import asyncio
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import httpx
from fastapi import Depends, FastAPI, Request

from audit_logging.application import dispatcher, services
from audit_logging.infrastructure.persistence import repositories
from audit_logging.infrastructure.persistence.bootstrap import ensure_audit_logging_schema
from audit_logging.interfaces.http.middleware import AuditHttpLoggingMiddleware, request_tenant_id, should_record_visitor
from audit_logging.interfaces.http.router import router as audit_router
from system.application.tenancy import reset_tenant_scope, set_tenant_scope
from system.application.database import connect
from system.domain.tenancy import TenantScope
from system.infrastructure.persistence.connection import configure_sql_observer
from system.interfaces.http import request_id_var


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

    def test_system_log_flushes_to_database(self) -> None:
        dispatcher.start_worker()
        accepted = dispatcher.record_system_log(
            {
                "tenant_id": 0,
                "event_action": "audit.worker.start",
                "source_module": "audit_logging",
                "summary": "审计日志后台写入任务已启动",
            }
        )
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
        self.assertEqual(response["items"][0]["event_action"], "audit.worker.start")

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
        self.assertEqual(item["tenant_id"], 0)
        self.assertEqual(item["event_outcome"], "failed")
        self.assertNotIn("secret", item["sql_template"])
        self.assertIn("id = ?", item["sql_template"])

    def test_api_middleware_reads_tenant_from_request_state(self) -> None:
        request = SimpleNamespace(
            state=SimpleNamespace(
                tenant_scope=TenantScope(
                    tenant_id=7,
                    tenant_key="default",
                    tenant_name="Default Tenant",
                )
            )
        )

        self.assertEqual(request_tenant_id(request), 7)

    def test_api_middleware_records_request_state_tenant_after_call_next(self) -> None:
        async def attach_scope(request: Request) -> None:
            request.state.tenant_scope = TenantScope(
                tenant_id=11,
                tenant_key="tenant-eleven",
                tenant_name="Tenant Eleven",
                principal_id=20,
                principal_name="operator",
            )

        app = FastAPI()
        app.add_middleware(AuditHttpLoggingMiddleware)

        @app.get("/demo")
        async def demo(_: None = Depends(attach_scope)) -> dict[str, bool]:
            return {"ok": True}

        async def call_demo() -> httpx.Response:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.get("/demo")

        dispatcher.start_worker()
        response = asyncio.run(call_demo())
        self.assertEqual(response.status_code, 200)

        dispatcher.stop_worker()
        dispatcher.flush_now()

        response = services.list_logs(
            category="api",
            page=1,
            page_size=20,
            current_user={"id": 20, "tenant_id": 11, "current_tenant": {"id": 11}},
        )
        self.assertEqual(response["pagination"]["total"], 1)
        self.assertEqual(response["items"][0]["tenant_id"], 11)

        visitor_response = services.list_logs(
            category="visitor",
            page=1,
            page_size=20,
            current_user={"id": 20, "tenant_id": 11, "current_tenant": {"id": 11}},
        )
        self.assertEqual(visitor_response["pagination"]["total"], 1)
        visitor_item = visitor_response["items"][0]
        self.assertEqual(visitor_item["tenant_id"], 11)
        self.assertEqual(visitor_item["entry_path"], "/demo")
        self.assertEqual(visitor_item["actor_user_id"], 20)
        self.assertEqual(visitor_item["actor_name"], "operator")
        self.assertEqual(visitor_item["actor_type"], "user")

    def test_visitor_track_endpoint_flushes_to_database(self) -> None:
        app = FastAPI()
        app.include_router(audit_router)
        request_token = request_id_var.set("req_visitor_track")

        async def call_track() -> httpx.Response:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.post(
                    "/audit-logs/visitors/track",
                    json={
                        "path": "/platform",
                        "title": "平台信息",
                        "visitor_id": "visitor-1",
                        "session_id": "session-1",
                        "device_type": "desktop",
                    },
                    headers={"user-agent": "pytest"},
                )

        dispatcher.start_worker()
        try:
            response = asyncio.run(call_track())
            self.assertEqual(response.status_code, 200)
        finally:
            request_id_var.reset(request_token)

        dispatcher.stop_worker()
        dispatcher.flush_now()

        response = services.list_logs(
            category="visitor",
            page=1,
            page_size=20,
            current_user={"id": 1, "tenant_id": 0, "current_tenant": {"id": 0}, "is_platform_admin": True},
        )
        self.assertEqual(response["pagination"]["total"], 1)
        self.assertEqual(response["items"][0]["entry_path"], "/platform")
        self.assertEqual(response["items"][0]["request_id"], "req_visitor_track")
        self.assertEqual(response["items"][0]["actor_name"], "")
        self.assertEqual(response["items"][0]["actor_type"], "anonymous")
        self.assertEqual(response["items"][0]["summary"], "访客访问 平台信息")

    def test_visitor_policy_skips_regular_api_paths(self) -> None:
        self.assertTrue(should_record_visitor("/"))
        self.assertTrue(should_record_visitor("/api/auth/login"))
        self.assertTrue(should_record_visitor("/api/login"))
        self.assertFalse(should_record_visitor("/api/users"))
        self.assertFalse(should_record_visitor("/api/audit-logs/api"))

    def test_sql_observer_uses_current_tenant_scope(self) -> None:
        dispatcher.start_worker()
        request_token = request_id_var.set("req_sql_context")
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
            request_id_var.reset(request_token)
        dispatcher.stop_worker()
        dispatcher.flush_now()

        response = services.list_logs(
            category="sql",
            page=1,
            page_size=20,
            current_user={"id": 10, "tenant_id": 7, "current_tenant": {"id": 7}},
        )
        self.assertEqual(response["pagination"]["total"], 1)
        item = response["items"][0]
        self.assertEqual(item["tenant_id"], 7)
        self.assertEqual(item["request_id"], "req_sql_context")
        self.assertEqual(item["actor_user_id"], 10)
        self.assertEqual(item["actor_name"], "tenant-admin")
        self.assertEqual(item["actor_type"], "user")

    def test_sql_observer_skips_successful_schema_introspection_sql(self) -> None:
        dispatcher.start_worker()
        for sql in (
            "PRAGMA table_info(appearance_themes)",
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            "SELECT 1 FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = ?",
            "SELECT 1 FROM pg_catalog.pg_indexes WHERE indexname = ?",
        ):
            dispatcher.observe_sql(
                sql=sql,
                params=("appearance_themes",),
                duration_ms=6000,
                success=True,
                error_message="",
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
        self.assertEqual(response["pagination"]["total"], 0)

    def test_sql_observer_records_failed_schema_introspection_sql(self) -> None:
        dispatcher.start_worker()
        dispatcher.observe_sql(
            sql="PRAGMA table_info(missing_table)",
            params=(),
            duration_ms=1,
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
        self.assertEqual(response["items"][0]["event_outcome"], "failed")

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
