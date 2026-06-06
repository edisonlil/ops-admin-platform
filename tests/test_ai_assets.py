from __future__ import annotations

import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest import mock

from ai_service_api import AIExecuteResult, register_ai_service, reset_ai_service
from ai_assets.application import services
from ai_assets.infrastructure.persistence import repositories
from ai_assets.infrastructure.persistence.bootstrap import ensure_ai_assets_schema
from system.application.data_access import (
    DataAccessPredicate,
    ResourceDescriptor,
    TenantOnlyDataAccessFilterProvider,
    configure_data_access_filter_provider,
)


class SelfOnlyProvider:
    def resolve_filter(self, *, current_user: dict[str, object], resource: ResourceDescriptor, action: str) -> DataAccessPredicate:
        current = current_user.get("current_tenant") if isinstance(current_user.get("current_tenant"), dict) else {}
        tenant_id = int((current or {}).get("id") or current_user.get("tenant_id") or 0)
        return DataAccessPredicate(tenant_id=tenant_id, scope="self", user_id=int(current_user.get("id") or 0))


class FakeAIService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute(self, capability_key, variables, *, options=None):  # type: ignore[no-untyped-def]
        self.calls.append((capability_key, dict(variables)))
        return AIExecuteResult(answer=f"润色：{variables['prompt']}", trace_id="trace_test", usage={"total_tokens": 3})


class AIAssetsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "ai-assets.db"
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
            "id": 10,
            "username": "owner",
            "current_tenant": {"id": 7, "tenant_key": "tenant-a", "name": "Tenant A"},
            "tenant_id": 7,
        }
        services.configure_repository(repositories)
        self.initialize_db()

    def tearDown(self) -> None:
        configure_data_access_filter_provider(TenantOnlyDataAccessFilterProvider())
        reset_ai_service()
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

    def test_prompt_polish_uses_ai_service_contract(self) -> None:
        fake_ai_service = FakeAIService()
        register_ai_service(fake_ai_service)

        result = services.polish_prompt({"title": "销售话术", "prompt": "请分析 {{content}}"}, self.current_user)

        self.assertEqual(result["answer"], "润色：请分析 {{content}}")
        self.assertEqual(result["trace_id"], "trace_test")
        self.assertEqual(fake_ai_service.calls[0][0], "prompt.polish")
        self.assertEqual(fake_ai_service.calls[0][1]["title"], "销售话术")

    def test_prompt_polish_reports_unavailable_without_ai_capabilities(self) -> None:
        reset_ai_service()

        with self.assertRaises(Exception) as caught:
            services.polish_prompt({"title": "销售话术", "prompt": "请分析"}, self.current_user)

        self.assertEqual(getattr(caught.exception, "status_code", None), 503)
        self.assertIn("AI service is not available", str(getattr(caught.exception, "detail", "")))

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

    def test_prompt_asset_detail_and_delete_follow_self_data_scope(self) -> None:
        configure_data_access_filter_provider(SelfOnlyProvider())
        prompt = self.create_prompt()
        other_user = {**self.current_user, "id": 11, "username": "other"}

        self.assertEqual(services.get_prompt_asset(int(prompt["id"]), self.current_user)["item"]["id"], prompt["id"])
        with self.assertRaises(Exception) as caught:
            services.get_prompt_asset(int(prompt["id"]), other_user)
        with self.assertRaises(Exception) as delete_caught:
            services.delete_prompt_asset(int(prompt["id"]), other_user)

        self.assertEqual(getattr(caught.exception, "status_code", None), 404)
        self.assertEqual(getattr(delete_caught.exception, "status_code", None), 404)

    def test_published_prompt_asset_resolver_uses_current_published_version(self) -> None:
        prompt = self.create_prompt(prompt_key="assistant.system")
        first = self.create_version(int(prompt["id"]), version="1.0.0")
        second = services.save_prompt_version(
            int(prompt["id"]),
            {
                "version": "2.0.0",
                "system_prompt": "",
                "developer_prompt": "",
                "user_prompt_template": "Use published prompt content for {{topic}}.",
                "variables_schema": {"type": "object", "required": ["topic"]},
                "output_schema": {},
                "render_engine": "simple",
                "status": "draft",
            },
            self.current_user,
        )["item"]

        services.publish_prompt_version(int(prompt["id"]), int(first["id"]), self.current_user)
        services.publish_prompt_version(int(prompt["id"]), int(second["id"]), self.current_user)

        published = services.list_published_prompt_assets(current_user=self.current_user)["items"]
        resolved = services.get_published_prompt_asset("assistant.system", self.current_user)

        self.assertEqual([item["prompt_key"] for item in published], ["assistant.system"])
        self.assertEqual(resolved["asset_key"], "assistant.system")
        self.assertEqual(resolved["resolved_version"], "2.0.0")
        self.assertEqual(resolved["system_prompt"], "Use published prompt content for {{topic}}.")
        self.assertEqual(resolved["variables_schema"]["required"], ["topic"])

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

    def test_prompt_asset_name_must_be_unique_in_tenant(self) -> None:
        first = self.create_prompt(prompt_key="meeting.summary")

        with self.assertRaises(Exception) as caught:
            services.save_prompt_asset(
                {
                    "prompt_key": "meeting.summary.copy",
                    "name": first["name"],
                    "description": "",
                    "tags": ["summary"],
                    "status": "draft",
                },
                self.current_user,
            )

        self.assertEqual(getattr(caught.exception, "status_code", None), 409)

    def test_prompt_and_skill_assets_filter_by_tags_before_pagination(self) -> None:
        self.create_prompt(prompt_key="meeting.summary", tags=["会议", "总结"])
        self.create_prompt(prompt_key="contract.summary", tags=["合同"])
        self.create_skill(skill_key="contract.review", tags=["合同", "审阅"])
        self.create_skill(skill_key="meeting.review", tags=["会议"])

        prompt_payload = services.list_prompt_assets(
            page=1,
            page_size=20,
            current_user=self.current_user,
            tags=["合同"],
        )
        skill_payload = services.list_skill_assets(
            page=1,
            page_size=20,
            current_user=self.current_user,
            tags="合同,审阅",
        )

        self.assertEqual([item["prompt_key"] for item in prompt_payload["items"]], ["contract.summary"])
        self.assertEqual(prompt_payload["pagination"]["total"], 1)
        self.assertEqual([item["skill_key"] for item in skill_payload["items"]], ["contract.review"])
        self.assertEqual(skill_payload["pagination"]["total"], 1)

    def test_copy_prompt_asset_creates_draft_with_unique_name_and_versions(self) -> None:
        prompt = self.create_prompt(prompt_key="meeting.summary", tags=["chatbot"])
        first = self.create_version(int(prompt["id"]), version="1.0.0")
        second = self.create_version(int(prompt["id"]), version="2.0.0")
        services.publish_prompt_version(int(prompt["id"]), int(second["id"]), self.current_user)

        copied = services.copy_prompt_asset(int(prompt["id"]), self.current_user)["item"]
        copied_versions = services.list_prompt_versions(int(copied["id"]), self.current_user)["items"]

        self.assertEqual(copied["name"], "meeting.summary 副本")
        self.assertEqual(copied["status"], "draft")
        self.assertEqual(copied["tags"], ["chatbot"])
        self.assertNotEqual(copied["prompt_key"], prompt["prompt_key"])
        self.assertEqual(len(copied_versions), 2)
        self.assertEqual({item["version"] for item in copied_versions}, {first["version"], second["version"]})
        self.assertEqual({item["status"] for item in copied_versions}, {"draft"})
        self.assertTrue(any(item["user_prompt_template"] == second["user_prompt_template"] for item in copied_versions))

        second_copy = services.copy_prompt_asset(int(prompt["id"]), self.current_user)["item"]
        self.assertEqual(second_copy["name"], "meeting.summary 副本 2")

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

    def test_prompt_asset_cannot_be_archived_when_referenced(self) -> None:
        prompt = self.create_prompt(prompt_key="meeting.summary")

        def referenced(tenant_id: int, prompt_key: str) -> bool:
            return tenant_id == 7 and prompt_key == "meeting.summary"

        services.register_prompt_asset_reference_checker(referenced)
        try:
            with self.assertRaises(Exception) as caught:
                services.delete_prompt_asset(int(prompt["id"]), self.current_user)
        finally:
            services.unregister_prompt_asset_reference_checker(referenced)

        self.assertEqual(getattr(caught.exception, "status_code", None), 409)

    def test_delete_archived_prompt_asset_removes_it_from_lists(self) -> None:
        prompt = self.create_prompt()

        archived = services.delete_prompt_asset(int(prompt["id"]), self.current_user)
        deleted = services.delete_prompt_asset(int(prompt["id"]), self.current_user)
        archived_items = services.list_prompt_assets(
            page=1,
            page_size=20,
            current_user=self.current_user,
            status_filter="archived",
        )["items"]

        self.assertTrue(archived["archived"])
        self.assertTrue(deleted["deleted"])
        self.assertEqual(archived_items, [])

    def test_skill_upload_creates_asset_and_version_with_hash(self) -> None:
        uploaded = services.upload_skill_asset(
            {
                "version": "1.0.0",
                "filename": "contract-review.zip",
                "package_bytes": self.sample_skill_zip(),
            },
            self.current_user,
        )

        item = uploaded["item"]
        version = uploaded["version"]

        self.assertEqual(item["tenant_id"], 7)
        self.assertEqual(item["name"], "contract-review")
        self.assertEqual(item["description"], "审阅合同风险")
        self.assertEqual(item["status"], "draft")
        self.assertEqual(version["entrypoint"], "SKILL.md")
        self.assertEqual(version["manifest"]["name"], "contract-review")
        self.assertEqual(len(version["content_sha256"]), 64)
        self.assertEqual(len(version["package_sha256"]), 64)
        self.assertGreater(version["package_size"], 0)
        self.assertIn("SKILL.md", [entry["path"] for entry in version["package_files"]])
        self.assertTrue(version["validation_report"]["valid"])

    def test_skill_upload_preserves_runtime_package_metadata(self) -> None:
        buffer = BytesIO()
        skill_md = "\n".join(
            [
                "---",
                "name: package-tool",
                "description: package runner",
                "runtime:",
                "  kind: sandbox_python",
                "  entrypoint: scripts/main.py",
                "  requirements: scripts/requirements.txt",
                "---",
                "",
                "Run the packaged script.",
            ]
        )
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("SKILL.md", skill_md)
            archive.writestr("scripts/main.py", "result = {'ok': True}")
            archive.writestr("scripts/requirements.txt", "requests==2.32.3\n")

        uploaded = services.upload_skill_asset(
            {
                "version": "1.0.0",
                "filename": "package-tool.zip",
                "package_bytes": buffer.getvalue(),
            },
            self.current_user,
        )

        version = uploaded["version"]
        self.assertEqual(version["entrypoint"], "scripts/main.py")
        self.assertEqual(version["manifest"]["runtime"]["kind"], "sandbox_python")
        self.assertEqual(version["runtime_constraints"]["requirements"], "scripts/requirements.txt")
        self.assertIn("scripts/main.py", [entry["path"] for entry in version["package_files"]])

    def test_published_skill_http_payload_does_not_expose_package_body(self) -> None:
        skill = self.create_skill(skill_key="contract.review")
        version = self.create_skill_version(int(skill["id"]), version="1.0.0")
        services.publish_skill_version(int(skill["id"]), int(version["id"]), self.current_user)

        http_payload = services.get_published_skill_asset("contract.review", self.current_user)
        runtime_payload = services.resolve_published_skill(skill_key="contract.review", tenant_id=7)

        self.assertNotIn("package_data_base64", http_payload)
        self.assertIn("package_data_base64", runtime_payload)
        self.assertTrue(runtime_payload["package_data_base64"])

    def test_skill_version_publish_makes_version_immutable(self) -> None:
        skill = self.create_skill()
        version = self.create_skill_version(int(skill["id"]), version="1.0.0")

        published = services.publish_skill_version(int(skill["id"]), int(version["id"]), self.current_user)["item"]

        self.assertEqual(published["status"], "published")
        with self.assertRaises(Exception) as caught:
            services.save_skill_version(
                int(skill["id"]),
                {
                    **version,
                    "filename": "contract-review.zip",
                    "package_bytes": self.sample_skill_zip("changed"),
                },
                self.current_user,
                version_id=int(version["id"]),
            )
        self.assertEqual(getattr(caught.exception, "status_code", None), 409)

    def test_published_skill_asset_resolver_uses_current_published_version(self) -> None:
        skill = self.create_skill(skill_key="contract.review")
        first = self.create_skill_version(int(skill["id"]), version="1.0.0", body="first")
        second = self.create_skill_version(int(skill["id"]), version="2.0.0", body="second")

        services.publish_skill_version(int(skill["id"]), int(first["id"]), self.current_user)
        services.publish_skill_version(int(skill["id"]), int(second["id"]), self.current_user)

        published = services.list_published_skill_assets(current_user=self.current_user)["items"]
        resolved = services.get_published_skill_asset("contract.review", self.current_user)

        self.assertEqual([item["skill_key"] for item in published], ["contract.review"])
        self.assertEqual(resolved["asset_key"], "contract.review")
        self.assertEqual(resolved["resolved_version"], "2.0.0")
        self.assertIn("second", resolved["content"])
        self.assertEqual(resolved["entrypoint"], "SKILL.md")

    def test_cannot_deprecate_only_published_skill_version(self) -> None:
        skill = self.create_skill()
        version = self.create_skill_version(int(skill["id"]), version="1.0.0")
        services.publish_skill_version(int(skill["id"]), int(version["id"]), self.current_user)

        with self.assertRaises(Exception) as caught:
            services.deprecate_skill_version(int(skill["id"]), int(version["id"]), self.current_user)

        self.assertEqual(getattr(caught.exception, "status_code", None), 409)
        versions = services.list_skill_versions(int(skill["id"]), self.current_user)["items"]
        self.assertEqual(versions[0]["status"], "published")

    def test_skill_asset_cannot_be_archived_when_referenced(self) -> None:
        skill = self.create_skill(skill_key="contract.review")

        def referenced(tenant_id: int, skill_key: str) -> bool:
            return tenant_id == 7 and skill_key == "contract.review"

        services.register_skill_asset_reference_checker(referenced)
        try:
            with self.assertRaises(Exception) as caught:
                services.delete_skill_asset(int(skill["id"]), self.current_user)
        finally:
            services.unregister_skill_asset_reference_checker(referenced)

        self.assertEqual(getattr(caught.exception, "status_code", None), 409)

    def test_skill_asset_detail_and_delete_follow_self_data_scope(self) -> None:
        configure_data_access_filter_provider(SelfOnlyProvider())
        skill = self.create_skill()
        other_user = {**self.current_user, "id": 11, "username": "other"}

        self.assertEqual(services.get_skill_asset(int(skill["id"]), self.current_user)["item"]["id"], skill["id"])
        with self.assertRaises(Exception) as caught:
            services.get_skill_asset(int(skill["id"]), other_user)
        with self.assertRaises(Exception) as delete_caught:
            services.delete_skill_asset(int(skill["id"]), other_user)

        self.assertEqual(getattr(caught.exception, "status_code", None), 404)
        self.assertEqual(getattr(delete_caught.exception, "status_code", None), 404)

    def test_invalid_skill_upload_requires_zip_package(self) -> None:
        with self.assertRaises(Exception) as caught:
            services.upload_skill_asset({"filename": "skill.md", "package_bytes": b"name: Empty"}, self.current_user)

        self.assertEqual(getattr(caught.exception, "status_code", None), 422)

    def test_invalid_skill_upload_requires_skill_md_in_zip(self) -> None:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("README.md", "missing entrypoint")

        with self.assertRaises(Exception) as caught:
            services.upload_skill_asset(
                {"filename": "missing-entrypoint.zip", "package_bytes": buffer.getvalue()},
                self.current_user,
            )

        self.assertEqual(getattr(caught.exception, "status_code", None), 422)

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

    def create_skill(
        self,
        *,
        skill_key: str = "contract.review",
        tags: list[str] | None = None,
    ) -> dict[str, object]:
        return services.save_skill_asset(
            {
                "skill_key": skill_key,
                "name": skill_key,
                "description": "审阅合同风险",
                "tags": tags or ["合同"],
                "status": "draft",
            },
            self.current_user,
        )["item"]

    def create_skill_version(self, skill_id: int, *, version: str, body: str = "review") -> dict[str, object]:
        return services.save_skill_version(
            skill_id,
            {
                "version": version,
                "filename": "contract-review.zip",
                "package_bytes": self.sample_skill_zip(body),
                "status": "draft",
            },
            self.current_user,
        )["item"]

    def sample_skill_zip(self, body: str = "review", path: str = "SKILL.md") -> bytes:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(path, self.sample_skill_content(body))
        return buffer.getvalue()

    def sample_skill_content(self, body: str = "review") -> str:
        return "\n".join(
            [
                "---",
                "name: contract-review",
                "description: 审阅合同风险",
                "---",
                "",
                f"# Contract Review {body}",
                "",
                "请识别合同中的风险条款。",
            ]
        )

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
