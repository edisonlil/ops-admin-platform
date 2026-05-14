from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ai_assets.application import services
from ai_assets.infrastructure.persistence.bootstrap import ensure_ai_assets_schema


class AIAssetsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "ai-assets.db"
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
        self.current_user = {
            "id": 10,
            "username": "owner",
            "current_tenant": {"id": 7, "tenant_key": "tenant-a", "name": "Tenant A"},
            "tenant_id": 7,
        }
        self.initialize_db()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def initialize_db(self) -> None:
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_ai_assets_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def mark_prompt_versions_deprecated(self, prompt_id: int) -> None:
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("UPDATE prompt_versions SET status = 'deprecated' WHERE prompt_id = ?", (prompt_id,))
            conn.commit()
        finally:
            conn.close()

    def test_prompt_version_publish_makes_version_immutable(self) -> None:
        prompt = self.create_prompt()
        version = self.create_version(int(prompt["id"]), version="1.0.0")

        published = services.publish_prompt_version(int(prompt["id"]), int(version["id"]), self.current_user)["item"]

        self.assertEqual(published["status"], "published")
        with self.assertRaises(Exception) as caught:
            services.save_prompt_version(
                int(prompt["id"]),
                {
                    **version,
                    "system_prompt": "changed",
                },
                self.current_user,
                version_id=int(version["id"]),
            )

        self.assertEqual(getattr(caught.exception, "status_code", None), 409)

    def test_prompt_version_number_cannot_be_renamed_on_update(self) -> None:
        prompt = self.create_prompt()
        version = self.create_version(int(prompt["id"]), version="1.0.0")

        updated = services.save_prompt_version(
            int(prompt["id"]),
            {
                **version,
                "user_prompt_template": "Summarize and extract action items: {{transcript}}",
            },
            self.current_user,
            version_id=int(version["id"]),
        )["item"]

        self.assertEqual(updated["version"], "1.0.0")
        self.assertIn("action items", updated["user_prompt_template"])

        with self.assertRaises(Exception) as caught:
            services.save_prompt_version(
                int(prompt["id"]),
                {
                    **version,
                    "version": "2.0.0",
                },
                self.current_user,
                version_id=int(version["id"]),
            )

        self.assertEqual(getattr(caught.exception, "status_code", None), 409)

    def test_publishing_prompt_version_deprecates_previous_published_version(self) -> None:
        prompt = self.create_prompt()
        first = self.create_version(int(prompt["id"]), version="1.0.0")
        second = self.create_version(int(prompt["id"]), version="2.0.0")

        services.publish_prompt_version(int(prompt["id"]), int(first["id"]), self.current_user)
        published = services.publish_prompt_version(int(prompt["id"]), int(second["id"]), self.current_user)["item"]

        versions = services.list_prompt_versions(int(prompt["id"]), self.current_user)["items"]
        versions_by_id = {int(item["id"]): item for item in versions}

        self.assertEqual(published["status"], "published")
        self.assertEqual(versions_by_id[int(first["id"])]["status"], "deprecated")
        self.assertEqual(versions_by_id[int(second["id"])]["status"], "published")
        self.assertEqual(sum(1 for item in versions if item["status"] == "published"), 1)

    def test_cannot_deprecate_only_published_prompt_version(self) -> None:
        prompt = self.create_prompt()
        version = self.create_version(int(prompt["id"]), version="1.0.0")
        services.publish_prompt_version(int(prompt["id"]), int(version["id"]), self.current_user)

        with self.assertRaises(Exception) as caught:
            services.deprecate_prompt_version(int(prompt["id"]), int(version["id"]), self.current_user)

        self.assertEqual(getattr(caught.exception, "status_code", None), 409)
        versions = services.list_prompt_versions(int(prompt["id"]), self.current_user)["items"]
        self.assertEqual(versions[0]["status"], "published")

    def test_prompt_asset_status_is_derived_from_published_versions(self) -> None:
        prompt = self.create_prompt()
        version = self.create_version(int(prompt["id"]), version="1.0.0")

        services.publish_prompt_version(int(prompt["id"]), int(version["id"]), self.current_user)
        published_prompt = services.get_prompt_asset(int(prompt["id"]), self.current_user)["item"]
        self.assertEqual(published_prompt["status"], "published")

        self.mark_prompt_versions_deprecated(int(prompt["id"]))
        draft_prompt = services.get_prompt_asset(int(prompt["id"]), self.current_user)["item"]
        self.assertEqual(draft_prompt["status"], "draft")

    def test_requires_explicit_schema_initialization(self) -> None:
        missing_db = Path(self.temp_dir.name) / "missing-schema.db"
        missing_db.touch()
        with mock.patch("ai_assets.infrastructure.persistence.repositories.resolve_db_path", return_value=missing_db):
            with self.assertRaises(Exception) as caught:
                services.list_prompt_assets(page=1, page_size=20, current_user=self.current_user)

        self.assertEqual(getattr(caught.exception, "status_code", None), 503)
        self.assertIn("init_ai_assets.py", str(caught.exception.detail))

    def test_prompt_asset_response_fields_stay_tenant_scoped(self) -> None:
        prompt = services.save_prompt_asset(
            {
                "name": "Tenant Scope",
            },
            self.current_user,
        )["item"]

        self.assertEqual(prompt["tenant_id"], 7)
        self.assertRegex(str(prompt["prompt_key"]), r"^tenant_scope_[0-9a-f]{8}$")
        self.assertEqual(
            set(prompt),
            {
                "id",
                "tenant_id",
                "prompt_key",
                "name",
                "description",
                "tags",
                "status",
                "version_count",
                "create_time",
                "update_time",
            },
        )

    def test_prompt_asset_update_keeps_generated_key(self) -> None:
        prompt = services.save_prompt_asset(
            {
                "name": "Generated Prompt",
                "description": "first",
            },
            self.current_user,
        )["item"]

        updated = services.save_prompt_asset(
            {
                "name": "Renamed Prompt",
                "description": "second",
                "prompt_key": "attempted.change",
            },
            self.current_user,
            prompt_id=int(prompt["id"]),
        )["item"]

        self.assertEqual(updated["prompt_key"], prompt["prompt_key"])
        self.assertEqual(updated["name"], "Renamed Prompt")

    def test_archived_prompt_asset_remains_visible_in_archived_filter(self) -> None:
        prompt = self.create_prompt()

        archived = services.delete_prompt_asset(int(prompt["id"]), self.current_user)
        archived_items = services.list_prompt_assets(
            page=1,
            page_size=20,
            current_user=self.current_user,
            status_filter="archived",
        )["items"]

        self.assertTrue(archived["archived"])
        self.assertEqual(len(archived_items), 1)
        self.assertEqual(archived_items[0]["id"], prompt["id"])
        self.assertEqual(archived_items[0]["status"], "archived")

    def create_prompt(
        self,
        *,
        prompt_key: str = "voice.summary",
        tags: list[str] | None = None,
    ) -> dict[str, object]:
        return services.save_prompt_asset(
            {
                "prompt_key": prompt_key,
                "name": prompt_key,
                "description": "",
                "tags": tags or ["summary"],
                "status": "draft",
            },
            self.current_user,
        )["item"]

    def create_version(self, prompt_id: int, *, version: str) -> dict[str, object]:
        return services.save_prompt_version(
            prompt_id,
            {
                "version": version,
                "system_prompt": "Return JSON.",
                "developer_prompt": "",
                "user_prompt_template": "Summarize: {{transcript}}",
                "variables_schema": {"type": "object", "required": ["transcript"], "properties": {"transcript": {"type": "string"}}},
                "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
                "render_engine": "simple",
                "status": "draft",
            },
            self.current_user,
        )["item"]


if __name__ == "__main__":
    unittest.main()
