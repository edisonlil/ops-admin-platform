from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class InMemoryMenuPort:
    def __init__(self) -> None:
        self.menus: dict[str, dict[str, object]] = {}

    def upsert_page_menu(self, payload: dict[str, object]) -> dict[str, object]:
        self.menus[str(payload["menu_key"])] = dict(payload)
        return self.menus[str(payload["menu_key"])]

    def delete_page_menu(self, menu_key: str) -> dict[str, object] | None:
        return self.menus.pop(menu_key, None)


class PageDesignerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "ops-admin-page-designer-test.db"
        self.env_patch = mock.patch.dict(
            "os.environ",
            {
                "FG_AGENT_DATABASE_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-database.json"),
                "OPS_ADMIN_APPLICATION_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-application.json"),
                "FG_AGENT_DATABASE_URL": "",
                "SUPABASE_DB_URL": "",
                "DATABASE_URL": "",
                "FG_AGENT_DB_PATH": str(self.db_path),
            },
            clear=False,
        )
        self.env_patch.start()
        self.current_user = {
            "id": 7,
            "username": "admin",
            "tenant_id": 1,
            "current_tenant": {"id": 1, "tenant_key": "default"},
            "permissions": ["page_designer:page:manage", "page_designer:page:view"],
        }
        self.menu_port = InMemoryMenuPort()
        self.initialize_db()
        self.configure_services()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def initialize_db(self) -> None:
        from page_designer.infrastructure.persistence.bootstrap import ensure_page_designer_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_page_designer_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def configure_services(self) -> None:
        from page_designer.application import services
        from page_designer.infrastructure.persistence import repositories

        services.configure_repository(repositories)
        services.configure_menu_port(self.menu_port)

    def test_page_can_be_created_saved_published_rendered_and_mounted(self) -> None:
        from page_designer.application import services

        created = services.create_page(
            {
                "page_key": "ops-dashboard",
                "name": "运营仪表盘",
                "description": "核心经营指标",
                "page_type": "dashboard",
            },
            self.current_user,
        )["item"]

        self.assertEqual(created["status"], "draft")

        draft = services.save_draft(
            int(created["id"]),
            {
                "layout": {
                    "cols": 24,
                    "rowHeight": 64,
                    "items": [{"id": "w_1", "type": "metric_card", "x": 0, "y": 0, "w": 6, "h": 3}],
                },
                "components": [{"id": "w_1", "type": "metric_card", "title": "收入", "props": {"value": "100万"}}],
            },
            self.current_user,
        )["item"]

        self.assertEqual(draft["version"]["components"][0]["title"], "收入")

        published = services.publish_page(int(created["id"]), self.current_user)["item"]
        self.assertEqual(published["status"], "published")
        self.assertIsNotNone(published["current_version_id"])

        runtime = services.runtime_page("ops-dashboard", self.current_user)["item"]
        self.assertEqual(runtime["runtime"]["page_key"], "ops-dashboard")
        self.assertEqual(runtime["runtime"]["components"][0]["type"], "metric_card")

        mounted = services.mount_menu(int(created["id"]), {}, self.current_user)["item"]
        self.assertEqual(mounted["mount"]["menu_key"], "page-designer-runtime-ops-dashboard")
        self.assertIn("page-designer-runtime-ops-dashboard", self.menu_port.menus)

        services.unmount_menu(int(created["id"]), self.current_user)
        self.assertNotIn("page-designer-runtime-ops-dashboard", self.menu_port.menus)

    def test_list_pages_uses_backend_pagination(self) -> None:
        from page_designer.application import services

        for index in range(3):
            services.create_page(
                {
                    "page_key": f"dashboard-{index}",
                    "name": f"仪表盘 {index}",
                    "page_type": "dashboard",
                },
                self.current_user,
            )

        first_page = services.list_pages(
            page=1,
            page_size=2,
            keyword="",
            page_type=None,
            status=None,
            current_user=self.current_user,
        )

        self.assertEqual(len(first_page["items"]), 2)
        self.assertEqual(first_page["pagination"], {"page": 1, "page_size": 2, "total": 3})

    def test_invalid_layout_is_rejected(self) -> None:
        from page_designer.application import services
        from page_designer.domain.exceptions import PageDesignerDomainError

        created = services.create_page(
            {"page_key": "bad-layout", "name": "异常布局", "page_type": "dashboard"},
            self.current_user,
        )["item"]

        with self.assertRaises(PageDesignerDomainError):
            services.save_draft(
                int(created["id"]),
                {
                    "layout": {
                        "cols": 24,
                        "rowHeight": 64,
                        "items": [{"id": "w_1", "x": 23, "y": 0, "w": 4, "h": 3}],
                    },
                    "components": [{"id": "w_1", "type": "metric_card"}],
                },
                self.current_user,
            )

    def test_missing_schema_returns_operational_error(self) -> None:
        from page_designer.infrastructure.persistence.bootstrap import require_page_designer_schema

        conn = sqlite3.connect(":memory:")
        try:
            with self.assertRaisesRegex(RuntimeError, "init_page_designer.py"):
                require_page_designer_schema(conn)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
