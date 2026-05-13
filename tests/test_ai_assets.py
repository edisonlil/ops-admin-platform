from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from framework.llm_core import LLMResponse

from ai_assets.application import services
from ai_assets.infrastructure.persistence.bootstrap import ensure_ai_assets_schema
from llm_runtime.infrastructure.persistence.bootstrap import ensure_llm_schema
from llm_runtime.infrastructure.persistence import repositories as llm_repositories


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
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_ai_assets_schema(conn)
            ensure_llm_schema(conn)
            self.seed_llm_route(conn)
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

    def test_contract_compatible_prompts_and_binding_are_scope_limited(self) -> None:
        prompt = self.create_prompt(owner_context="voice_analysis", category="analysis", tags=["summary"])
        version = self.create_version(int(prompt["id"]), version="1.0.0")
        contract = self.create_contract(
            allowed_prompt_scopes={
                "owner_contexts": ["voice_analysis"],
                "categories": ["analysis"],
                "tags": ["summary"],
            }
        )

        compatible = services.compatible_prompts("voice_analysis.transcript.summary", self.current_user)

        self.assertEqual(len(compatible["items"]), 1)
        binding = services.create_binding(
            {
                "contract_id": contract["id"],
                "prompt_id": prompt["id"],
                "prompt_version_id": version["id"],
                "binding_name": "Default",
                "environment": "prod",
            },
            self.current_user,
        )["item"]
        self.assertEqual(binding["contract_key"], "voice_analysis.transcript.summary")

        other_prompt = self.create_prompt(prompt_key="wrong.owner", owner_context="other", category="analysis")
        other_version = self.create_version(int(other_prompt["id"]), version="1.0.0")
        with self.assertRaises(Exception) as caught:
            services.create_binding(
                {
                    "contract_id": contract["id"],
                    "prompt_id": other_prompt["id"],
                    "prompt_version_id": other_version["id"],
                },
                self.current_user,
            )

        self.assertEqual(getattr(caught.exception, "status_code", None), 422)

    def test_execute_prompt_renders_messages_calls_llm_and_records_run(self) -> None:
        prompt = self.create_prompt(owner_context="voice_analysis", category="analysis")
        version = self.create_version(int(prompt["id"]), version="1.0.0")
        contract = self.create_contract()
        services.create_binding(
            {
                "contract_id": contract["id"],
                "prompt_id": prompt["id"],
                "prompt_version_id": version["id"],
                "environment": "prod",
            },
            self.current_user,
        )

        with mock.patch(
            "ai_assets.application.services.llm_gateway.generate",
            return_value=LLMResponse(content='{"summary":"done"}', elapsed_seconds=0.03),
        ) as generate:
            result = services.execute_prompt(
                {
                    "contract_key": "voice_analysis.transcript.summary",
                    "variables": {"transcript": "hello"},
                    "correlation_id": "corr-1",
                },
                self.current_user,
            )

        self.assertTrue(result["schema_valid"])
        self.assertEqual(result["output_json"], {"summary": "done"})
        self.assertEqual(result["run"]["status"], "succeeded")
        self.assertEqual(result["run"]["correlation_id"], "corr-1")
        self.assertIn("hello", result["rendered_messages"][-1]["content"])
        self.assertEqual(generate.call_args.kwargs["task_key"], "voice_analysis.summary")
        runs = services.list_runs(page=1, page_size=20, current_user=self.current_user)
        self.assertEqual(runs["pagination"]["total"], 1)

    def test_requires_explicit_schema_initialization(self) -> None:
        missing_db = Path(self.temp_dir.name) / "missing-schema.db"
        missing_db.touch()
        with mock.patch("ai_assets.infrastructure.persistence.repositories.resolve_db_path", return_value=missing_db):
            with self.assertRaises(Exception) as caught:
                services.list_prompt_assets(page=1, page_size=20, current_user=self.current_user)

        self.assertEqual(getattr(caught.exception, "status_code", None), 503)
        self.assertIn("init_ai_assets.py", str(caught.exception.detail))

    def create_prompt(
        self,
        *,
        prompt_key: str = "voice.summary",
        owner_context: str = "voice_analysis",
        category: str = "analysis",
        tags: list[str] | None = None,
    ) -> dict[str, object]:
        return services.save_prompt_asset(
            {
                "prompt_key": prompt_key,
                "name": prompt_key,
                "description": "",
                "category": category,
                "tags": tags or ["summary"],
                "owner_context": owner_context,
                "visibility": "tenant",
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

    def create_contract(self, *, allowed_prompt_scopes: dict[str, object] | None = None) -> dict[str, object]:
        return services.save_contract(
            {
                "contract_key": "voice_analysis.transcript.summary",
                "owner_context": "voice_analysis",
                "task_kind": "single_call",
                "display_name": "Transcript Summary",
                "llm_task_key": "voice_analysis.summary",
                "input_schema": {"type": "object", "required": ["transcript"], "properties": {"transcript": {"type": "string"}}},
                "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
                "allowed_prompt_scopes": allowed_prompt_scopes or {"owner_contexts": ["voice_analysis"], "categories": ["analysis"]},
                "enabled": True,
            },
            self.current_user,
        )["item"]

    @staticmethod
    def seed_llm_route(conn: sqlite3.Connection) -> None:
        llm_repositories.upsert_provider(
            conn,
            {
                "provider_key": "test",
                "display_name": "Test",
                "base_url": "https://test.example/v1",
                "api_key": "sk-test",
                "enabled": True,
            },
        )
        llm_repositories.upsert_model(
            conn,
            {
                "model_key": "test.model",
                "provider_key": "test",
                "model_name": "test-model",
                "enabled": True,
            },
        )
        llm_repositories.register_task(
            conn,
            {
                "task_key": "voice_analysis.summary",
                "display_name": "Voice Summary",
                "owner_context": "voice_analysis",
            },
        )
        llm_repositories.upsert_routing_policy(
            conn,
            {
                "route_key": "voice_analysis.summary",
                "strategy": "priority",
                "entries": [{"model_key": "test.model", "priority": 1, "response_format": "json"}],
            },
        )


if __name__ == "__main__":
    unittest.main()
