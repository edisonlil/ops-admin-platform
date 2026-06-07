from __future__ import annotations

import sqlite3
import unittest
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from unittest import mock
import json
import base64

from PIL import Image

from framework.llm_core import LLMResponse, OpenAICompatibleLLMClient
from ai_runtime_core.prompt_runtime import media_content_part
from ai_runtime_core.prompt_runtime import media_content_parts
from ai_capabilities.application import services as ai_capabilities
from ai_applications.application import services as ai_applications
from ai_applications.infrastructure.persistence.bootstrap import ensure_ai_applications_schema
from ai_applications.infrastructure.persistence.bootstrap import require_ai_agent_schema as require_ai_agent_schema_bootstrap
from ai_applications.infrastructure.persistence.bootstrap import require_ai_applications_schema as require_ai_applications_schema_bootstrap
from ai_applications.infrastructure.persistence.bootstrap import (
    require_prompt_runtime_trace_detail_schema as require_prompt_runtime_trace_detail_schema_bootstrap,
)
from ai_capabilities.infrastructure.persistence.bootstrap import ensure_ai_capabilities_schema
from ai_capabilities.infrastructure.persistence.bootstrap import require_ai_capabilities_schema as require_ai_capabilities_schema_bootstrap
from llm_runtime.application import gateway
from llm_runtime.application import services
from llm_runtime.infrastructure.persistence.bootstrap import ensure_llm_schema
from llm_runtime.infrastructure.persistence.bootstrap import require_llm_schema as require_llm_schema_bootstrap
from llm_runtime.infrastructure.persistence import repositories
from system.application.tenancy import reset_tenant_scope, set_tenant_scope
from system.application.data_access import DataAccessPredicate, SCOPE_SELF
from system.domain.tenancy import TenantScope
from ai_assets.infrastructure.persistence.bootstrap import ensure_ai_assets_schema
from ai_assets.infrastructure.persistence.bootstrap import require_ai_assets_schema as require_ai_assets_schema_bootstrap
from ai_assets.application import services as ai_asset_services
from ai_assets.infrastructure.persistence import repositories as ai_assets_repositories
from ai_applications.infrastructure.persistence import repositories as ai_applications_repositories
from ai_capabilities.infrastructure.persistence import repositories as ai_capabilities_repositories
from llm_runtime.infrastructure.persistence import repositories as llm_runtime_repositories


class LLMRuntimeTests(unittest.TestCase):
    _env_patch: mock._patch_dict | None = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._env_patch = mock.patch.dict(
            "os.environ",
            {
                "FG_AGENT_DATABASE_CONFIG": str(Path(".tmp") / "missing-database.json"),
                "OPS_ADMIN_APPLICATION_CONFIG": str(Path(".tmp") / "missing-application.json"),
                "FG_AGENT_DATABASE_URL": "",
                "SUPABASE_DB_URL": "",
                "DATABASE_URL": "",
            },
            clear=False,
        )
        cls._env_patch.start()
        llm_runtime_repositories.require_llm_schema = require_llm_schema_bootstrap
        ai_applications_repositories.require_ai_applications_schema = require_ai_applications_schema_bootstrap
        ai_applications_repositories.require_ai_agent_schema = require_ai_agent_schema_bootstrap
        ai_applications_repositories.require_prompt_runtime_trace_detail_schema = require_prompt_runtime_trace_detail_schema_bootstrap
        ai_capabilities_repositories.require_ai_capabilities_schema = require_ai_capabilities_schema_bootstrap
        ai_assets_repositories.require_ai_assets_schema = require_ai_assets_schema_bootstrap
        services.configure_repository(llm_runtime_repositories)
        gateway.configure_repository(llm_runtime_repositories)
        ai_applications.configure_repository(ai_applications_repositories)
        ai_capabilities.configure_repository(ai_capabilities_repositories)
        ai_asset_services.configure_repository(ai_assets_repositories)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._env_patch is not None:
            cls._env_patch.stop()
    def test_config_can_be_saved_read_and_resolved_for_runtime(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            payload = {
                "provider": "minimax",
                "model": "MiniMax-M2.7",
                "base_url": "https://api.minimaxi.com/v1",
                "api_key": "sk-test",
                "command": "",
                "timeout_seconds": 30,
                "temperature": 0.2,
                "extra_body": {"reasoning_split": True},
                "enable_think_output": True,
                "enabled": True,
            }
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                saved = services.save_llm_config(payload)
                visible = services.get_llm_config()

            runtime = services.runtime_llm_config(db_path)

            self.assertEqual(saved["provider"], "minimax")
            self.assertTrue(visible["api_key_configured"])
            self.assertNotIn("sk-test", str(visible))
            assert runtime is not None
            self.assertEqual(runtime["provider"], "minimax")
            self.assertEqual(runtime["minimax"]["api_key"], "sk-test")
            self.assertEqual(runtime["minimax"]["model"], "MiniMax-M2.7")
            self.assertTrue(runtime["minimax"]["enable_think_output"])
            self.assertTrue(visible["enable_think_output"])
        finally:
            self._unlink_db(db_path)

    def test_default_config_disables_think_output(self) -> None:
        response = services.default_llm_config_response(source="database")

        self.assertFalse(response["enable_think_output"])
        self.assertEqual(response["extra_body"], {})

    def test_llm_config_and_routes_are_tenant_scoped(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            tenant_a = set_tenant_scope(TenantScope(tenant_id=11, tenant_key="a", tenant_name="Tenant A"))
            try:
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    services.save_llm_config(
                        {
                            "provider": "minimax",
                            "model": "tenant-a-model",
                            "api_key": "sk-a",
                            "extra_body": {},
                            "enable_think_output": False,
                        }
                    )
                    visible_a = services.get_llm_config()
                self._seed_single_route(db_path, provider_key="dashscope", model_key="tenant-a.model")
            finally:
                reset_tenant_scope(tenant_a)

            tenant_b = set_tenant_scope(TenantScope(tenant_id=22, tenant_key="b", tenant_name="Tenant B"))
            try:
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    visible_b = services.get_llm_config()
                self._seed_single_route(db_path, provider_key="siliconflow", model_key="tenant-b.model")
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                try:
                    ensure_llm_schema(conn)
                    models_b = repositories.list_models(conn)
                    route_b = repositories.resolve_route(conn, "ops.sample.rank")
                finally:
                    conn.close()
            finally:
                reset_tenant_scope(tenant_b)

            self.assertEqual(visible_a["model"], "tenant-a-model")
            self.assertEqual(visible_b["source"], "database")
            self.assertFalse(visible_b["enabled"])
            self.assertEqual([item["model_key"] for item in models_b], ["tenant-b.model"])
            assert route_b is not None
            self.assertEqual(route_b.policy.entries[0].model_key, "tenant-b.model")
        finally:
            self._unlink_db(db_path)

    def test_routing_policy_resolves_task_and_fallback(self) -> None:
        db_path = self._temporary_db_path()
        sqlite3.connect(db_path).close()
        try:
            self._seed_route(db_path)
            calls: list[str] = []

            def fake_client_for_entry(entry: object, *, response_format: str | None = None) -> object:
                model_key = getattr(entry, "model_key")
                calls.append(str(model_key))

                class FakeClient:
                    def generate_response(self, prompt: str, *, enable_think_output: bool | None = None) -> LLMResponse:
                        if model_key == "dashscope.qwen-plus":
                            raise RuntimeError("HTTP 500 temporary unavailable")
                        return LLMResponse(
                            content="{\"decision\":\"matched\"}",
                            elapsed_seconds=0.12,
                            usage={"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
                        )

                return FakeClient()

            with mock.patch("llm_runtime.application.gateway.client_for_entry", side_effect=fake_client_for_entry):
                response = gateway.generate(
                    task_key="ops.sample.rank",
                    prompt="hello",
                    response_format="json",
                    database_target_override=db_path,
                )

            self.assertEqual(response.content, "{\"decision\":\"matched\"}")
            self.assertEqual(calls, ["dashscope.qwen-plus", "siliconflow.qwen3-32b"])
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                logs = [dict(row) for row in conn.execute("SELECT * FROM llm_call_logs ORDER BY id").fetchall()]
            finally:
                conn.close()
            self.assertEqual([item["status"] for item in logs], ["failed", "success"])
            self.assertEqual(logs[1]["is_fallback"], 1)
            self.assertEqual(logs[1]["total_tokens"], 7)
        finally:
            self._unlink_db(db_path)

    def test_runtime_config_routes_sample_rank_from_database(self) -> None:
        db_path = self._temporary_db_path()
        sqlite3.connect(db_path).close()
        try:
            self._seed_route(db_path)
            config = services.runtime_llm_config(db_path)
            assert config is not None

            client = services.build_llm_client(
                role="rank",
                config={**config, "role_task_map": {"rank": "ops.sample.rank"}},
            )

            self.assertIsInstance(client, services.RoutedLLMClient)
            assert isinstance(client, services.RoutedLLMClient)
            self.assertEqual(client.task_key, "ops.sample.rank")
        finally:
            self._unlink_db(db_path)

    def test_call_logs_are_scoped_by_current_user(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                tenant = set_tenant_scope(
                    TenantScope(
                        tenant_id=1,
                        tenant_key="default",
                        tenant_name="Default Tenant",
                        principal_id=7,
                        principal_name="alice",
                        principal_department_id=3,
                    )
                )
                try:
                    repositories.record_call_log(
                        conn,
                        {
                            "task_key": "ops.sample.rank",
                            "route_key": "ops.sample.rank",
                            "provider_key": "dashscope",
                            "model_key": "dashscope.qwen-plus",
                            "model_name": "qwen-plus",
                            "status": "success",
                        },
                    )
                finally:
                    reset_tenant_scope(tenant)
                tenant = set_tenant_scope(
                    TenantScope(
                        tenant_id=1,
                        tenant_key="default",
                        tenant_name="Default Tenant",
                        principal_id=8,
                        principal_name="bob",
                        principal_department_id=4,
                    )
                )
                try:
                    repositories.record_call_log(
                        conn,
                        {
                            "task_key": "ops.sample.rank",
                            "route_key": "ops.sample.rank",
                            "provider_key": "siliconflow",
                            "model_key": "siliconflow.qwen3-32b",
                            "model_name": "Qwen/Qwen3-32B",
                            "status": "failed",
                        },
                    )
                finally:
                    reset_tenant_scope(tenant)
                conn.commit()
                items, _ = repositories.list_call_logs(
                    conn,
                    data_scope=DataAccessPredicate(tenant_id=1, scope=SCOPE_SELF, user_id=7),
                )
            finally:
                conn.close()

            self.assertEqual([item["creator_id"] for item in items], [7])
            self.assertEqual(items[0]["owner_department_id"], 3)
            self.assertEqual(items[0]["model_key"], "dashscope.qwen-plus")
        finally:
            self._unlink_db(db_path)

    def test_openai_compatible_client_calls_chat_completions(self) -> None:
        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "choices": [{"message": {"content": "{\"ok\":true}"}}],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
                    }
                ).encode("utf-8")

        client = OpenAICompatibleLLMClient(
            provider_name="dashscope",
            api_key="sk-test",
            model="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            timeout_seconds=3,
            extra_body={"response_format": {"type": "json_object"}},
        )
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            response = client.generate_response("hello")

        self.assertEqual(response.content, "{\"ok\":true}")
        self.assertEqual(response.usage["total_tokens"], 3)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
        self.assertEqual(request.headers["Authorization"], "Bearer sk-test")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "qwen-plus")
        self.assertEqual(body["response_format"], {"type": "json_object"})

    def test_siliconflow_client_maps_audio_input_to_audio_url_part(self) -> None:
        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps({"choices": [{"message": {"content": "ok"}}], "usage": {}}).encode("utf-8")

        client = OpenAICompatibleLLMClient(
            provider_name="siliconflow",
            api_key="sk-test",
            model="Qwen/Qwen3-Omni-30B-A3B-Thinking",
            base_url="https://api.siliconflow.cn/v1",
            timeout_seconds=3,
        )
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            response = client.generate_chat_response(
                [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请转写"},
                            {"type": "input_audio", "input_audio": {"data": "abc", "format": "mp3"}},
                        ],
                    }
                ]
            )

        self.assertEqual(response.content, "ok")
        body = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        content = body["messages"][0]["content"]
        self.assertTrue(any(part.get("type") == "audio_url" for part in content))
        self.assertTrue(any(part.get("type") == "text" for part in content))
        audio_part = next(part for part in content if part.get("type") == "audio_url")
        self.assertEqual(audio_part["audio_url"]["url"], "data:audio/mpeg;base64,abc")

    def test_siliconflow_collapses_developer_role_into_system(self) -> None:
        """业务层会同时下发 system_prompt 和 developer_prompt 给 siliconflow。

        siliconflow 不认 role='developer'，会返回 400。client 层需要在出站前把
        developer 合并到 system 后面，附 ``## Developer Notes`` 分隔标题。
        """
        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps({"choices": [{"message": {"content": "ok"}}], "usage": {}}).encode("utf-8")

        client = OpenAICompatibleLLMClient(
            provider_name="siliconflow",
            api_key="sk-test",
            model="Qwen/Qwen3-32B",
            base_url="https://api.siliconflow.cn/v1",
            timeout_seconds=3,
        )
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            response = client.generate_chat_response(
                [
                    {"role": "system", "content": "you are an assistant"},
                    {"role": "developer", "content": "respond in chinese"},
                    {"role": "user", "content": "hi"},
                ]
            )

        self.assertEqual(response.content, "ok")
        body = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        messages = body["messages"]
        # 不再下发 role=developer
        self.assertEqual([m["role"] for m in messages], ["system", "user"])
        # developer 内容被合并到 system，并加 ## Developer Notes 标题
        system_content = messages[0]["content"]
        self.assertIn("you are an assistant", system_content)
        self.assertIn("## Developer Notes", system_content)
        self.assertIn("respond in chinese", system_content)

    def test_siliconflow_developer_without_system_promotes_to_system(self) -> None:
        """没有 system 时，第一段 developer 应被提升为 system。"""

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps({"choices": [{"message": {"content": "ok"}}], "usage": {}}).encode("utf-8")

        client = OpenAICompatibleLLMClient(
            provider_name="siliconflow",
            api_key="sk-test",
            model="Qwen/Qwen3-32B",
            base_url="https://api.siliconflow.cn/v1",
            timeout_seconds=3,
        )
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            client.generate_chat_response(
                [
                    {"role": "developer", "content": "be concise"},
                    {"role": "user", "content": "hi"},
                ]
            )

        body = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        messages = body["messages"]
        self.assertEqual([m["role"] for m in messages], ["system", "user"])
        self.assertEqual(messages[0]["content"], "be concise")

    def test_dashscope_collapses_developer_role_into_system(self) -> None:
        """dashscope（阿里百炼 OpenAI 兼容层）也不认 developer，必须降级。"""

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps({"choices": [{"message": {"content": "ok"}}], "usage": {}}).encode("utf-8")

        client = OpenAICompatibleLLMClient(
            provider_name="dashscope",
            api_key="sk-test",
            model="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            timeout_seconds=3,
        )
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            client.generate_chat_response(
                [
                    {"role": "system", "content": "sys"},
                    {"role": "developer", "content": "dev1"},
                    {"role": "developer", "content": "dev2"},
                    {"role": "user", "content": "hi"},
                ]
            )

        body = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        messages = body["messages"]
        self.assertEqual([m["role"] for m in messages], ["system", "user"])
        system_content = messages[0]["content"]
        self.assertIn("sys", system_content)
        self.assertIn("dev1", system_content)
        self.assertIn("dev2", system_content)
        # 两段 developer 都标注来源
        self.assertEqual(system_content.count("## Developer Notes"), 2)

    def test_openai_provider_preserves_developer_role(self) -> None:
        """OpenAI 原生 o 系列支持 role=developer，必须原样保留分层语义。"""

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps({"choices": [{"message": {"content": "ok"}}], "usage": {}}).encode("utf-8")

        client = OpenAICompatibleLLMClient(
            provider_name="openai",
            api_key="sk-test",
            model="o3-mini",
            base_url="https://api.openai.com/v1",
            timeout_seconds=3,
        )
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            client.generate_chat_response(
                [
                    {"role": "system", "content": "sys"},
                    {"role": "developer", "content": "dev"},
                    {"role": "user", "content": "hi"},
                ]
            )

        body = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        messages = body["messages"]
        self.assertEqual([m["role"] for m in messages], ["system", "developer", "user"])
        self.assertEqual(messages[1]["content"], "dev")

    def test_image_media_part_requires_supported_valid_data_url_or_remote_url(self) -> None:
        valid_png = self._image_data_url()

        image_part = media_content_part("image", {"type": "image", "name": "screen.png", "data_url": valid_png})
        self.assertEqual(image_part["type"], "image_url")
        self.assertTrue(image_part["image_url"]["url"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(
            media_content_part("image", {"type": "image", "name": "remote.png", "url": "https://example.com/remote.png"}),
            {"type": "image_url", "image_url": {"url": "https://example.com/remote.png"}},
        )
        self.assertEqual(
            media_content_part("image", {"type": "image", "name": "icon.svg", "data_url": "data:image/svg+xml;base64,PHN2Zz4="})["type"],
            "text",
        )
        self.assertEqual(
            media_content_part("image", {"type": "image", "name": "bad.png", "data_url": "data:image/png;base64,not valid"})["type"],
            "text",
        )
        self.assertEqual(
            media_content_part("image", {"type": "image", "name": "local.png", "preview_url": "/files/1/preview"})["type"],
            "text",
        )

    def test_image_media_variable_list_renders_multiple_image_parts(self) -> None:
        first = self._image_data_url(width=1600, height=900, color=(220, 30, 30))
        second = self._image_data_url(width=1400, height=800, color=(30, 30, 220))

        parts = media_content_parts(
            {
                "images": [
                    {"type": "image", "name": "first.png", "data_url": first},
                    {"type": "image", "name": "second.png", "data_url": second},
                ]
            }
        )

        self.assertEqual([part["type"] for part in parts], ["image_url", "image_url"])
        self.assertTrue(parts[0]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
        self.assertTrue(parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
        self.assertLess(len(parts[0]["image_url"]["url"]), 900 * 1024)
        self.assertLess(len(parts[1]["image_url"]["url"]), 900 * 1024)

    def test_openai_chat_completion_can_call_configured_model_key(self) -> None:
        db_path = self._temporary_db_path()
        sqlite3.connect(db_path).close()
        try:
            self._seed_route(db_path)

            def fake_client_for_entry(entry: object, *, response_format: str | None = None) -> object:
                class FakeClient:
                    def generate_chat_response(
                        self,
                        messages: list[dict[str, object]],
                        *,
                        extra_body: dict[str, object] | None = None,
                        enable_think_output: bool | None = None,
                    ) -> LLMResponse:
                        self.messages = messages
                        return LLMResponse(
                            content="direct ok",
                            elapsed_seconds=0.2,
                            usage={"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
                        )

                return FakeClient()

            with mock.patch("llm_runtime.application.gateway.database_target", return_value=db_path):
                with mock.patch("llm_runtime.application.gateway.client_for_entry", side_effect=fake_client_for_entry):
                    response = services.create_openai_chat_completion(
                        {
                            "model": "dashscope.qwen-plus",
                            "messages": [{"role": "user", "content": "ping"}],
                        }
                    )

            self.assertEqual(response["object"], "chat.completion")
            self.assertEqual(response["model"], "dashscope.qwen-plus")
            self.assertEqual(response["choices"][0]["message"]["content"], "direct ok")
            self.assertEqual(response["usage"]["total_tokens"], 7)
        finally:
            self._unlink_db(db_path)

    def test_openai_chat_completion_can_override_think_output(self) -> None:
        db_path = self._temporary_db_path()
        sqlite3.connect(db_path).close()
        try:
            self._seed_route(db_path)
            think_flags: list[bool | None] = []

            def fake_client_for_entry(entry: object, *, response_format: str | None = None) -> object:
                class FakeClient:
                    def generate_chat_response(
                        self,
                        messages: list[dict[str, object]],
                        *,
                        extra_body: dict[str, object] | None = None,
                        enable_think_output: bool | None = None,
                    ) -> LLMResponse:
                        think_flags.append(enable_think_output)
                        return LLMResponse(content="<think>plan</think>answer", elapsed_seconds=0.2)

                return FakeClient()

            with mock.patch("llm_runtime.application.gateway.database_target", return_value=db_path):
                with mock.patch("llm_runtime.application.gateway.client_for_entry", side_effect=fake_client_for_entry):
                    response = services.create_openai_chat_completion(
                        {
                            "model": "dashscope.qwen-plus",
                            "messages": [{"role": "user", "content": "ping"}],
                            "enable_think_output": True,
                        }
                    )

            self.assertEqual(think_flags, [True])
            self.assertEqual(response["choices"][0]["message"]["content"], "<think>plan</think>answer")
        finally:
            self._unlink_db(db_path)

    def test_openai_stream_response_uses_sse_chunks(self) -> None:
        response = {
            "id": "chatcmpl-test",
            "created": 123,
            "model": "dashscope.qwen-plus",
            "choices": [{"message": {"content": "hello"}}],
        }

        events = services.openai_chat_completion_stream_events(response)

        self.assertTrue(events[0].startswith("data: "))
        self.assertIn('"role": "assistant"', events[0])
        self.assertTrue(any('"content": "hello"' in event for event in events))
        self.assertEqual(events[-1], "data: [DONE]\n\n")

    def test_openai_stream_completion_proxies_provider_events(self) -> None:
        db_path = self._temporary_db_path()
        sqlite3.connect(db_path).close()
        try:
            self._seed_route(db_path)

            class FakeClient:
                def stream_chat_completions(
                    self,
                    messages: list[dict[str, object]],
                    *,
                    extra_body: dict[str, object] | None = None,
                    enable_think_output: bool | None = None,
                ) -> object:
                    yield 'data: {"choices":[{"delta":{"content":"1"}}]}\n\n'
                    yield 'data: {"choices":[{"delta":{"content":"2"}}]}\n\n'
                    yield "data: [DONE]\n\n"

            with mock.patch("llm_runtime.application.gateway.database_target", return_value=db_path):
                with mock.patch("llm_runtime.application.gateway.client_for_entry", return_value=FakeClient()):
                    events = list(
                        services.create_openai_chat_completion_stream(
                            {
                                "model": "dashscope.qwen-plus",
                                "messages": [{"role": "user", "content": "count"}],
                                "stream": True,
                            }
                        )
                    )

            self.assertEqual(events, [
                'data: {"choices":[{"delta":{"content":"1"}}]}\n\n',
                'data: {"choices":[{"delta":{"content":"2"}}]}\n\n',
                "data: [DONE]\n\n",
            ])
        finally:
            self._unlink_db(db_path)

    def test_openai_stream_completion_returns_error_event_for_provider_error(self) -> None:
        db_path = self._temporary_db_path()
        sqlite3.connect(db_path).close()
        try:
            self._seed_route(db_path)

            class FakeClient:
                def stream_chat_completions(
                    self,
                    messages: list[dict[str, object]],
                    *,
                    extra_body: dict[str, object] | None = None,
                    enable_think_output: bool | None = None,
                ) -> object:
                    raise RuntimeError("provider request failed: HTTP 401")
                    yield ""

            with mock.patch("llm_runtime.application.gateway.database_target", return_value=db_path):
                with mock.patch("llm_runtime.application.gateway.client_for_entry", return_value=FakeClient()):
                    events = list(
                        services.create_openai_chat_completion_stream(
                            {
                                "model": "dashscope.qwen-plus",
                                "messages": [{"role": "user", "content": "count"}],
                                "stream": True,
                            }
                        )
                    )

            self.assertEqual(len(events), 2)
            self.assertTrue(events[0].startswith("event: error\n"))
            self.assertIn("provider request failed: HTTP 401", events[0])
            self.assertEqual(events[1], "data: [DONE]\n\n")
        finally:
            self._unlink_db(db_path)

    def test_openai_chat_completion_can_call_route_key(self) -> None:
        db_path = self._temporary_db_path()
        sqlite3.connect(db_path).close()
        try:
            self._seed_route(db_path)

            def fake_client_for_entry(entry: object, *, response_format: str | None = None) -> object:
                class FakeClient:
                    def generate_response(self, prompt: str, *, enable_think_output: bool | None = None) -> LLMResponse:
                        return LLMResponse(content="route ok", elapsed_seconds=0.1)

                return FakeClient()

            with mock.patch("llm_runtime.application.gateway.database_target", return_value=db_path):
                with mock.patch("llm_runtime.application.gateway.client_for_entry", side_effect=fake_client_for_entry):
                    response = services.create_openai_chat_completion(
                        {
                            "model": "ops.sample.rank",
                            "messages": [{"role": "user", "content": "ping"}],
                        }
                    )

            self.assertEqual(response["model"], "ops.sample.rank")
            self.assertEqual(response["choices"][0]["message"]["content"], "route ok")
        finally:
            self._unlink_db(db_path)

    def test_ai_application_quota_blocks_new_applications(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            tenant = set_tenant_scope(TenantScope(tenant_id=33, tenant_key="quota", tenant_name="Quota Tenant"))
            try:
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        ai_applications.save_tenant_ai_quota(
                            33,
                            {
                                "max_applications": 1,
                                "max_capabilities": 10,
                                "max_assets": 10,
                                "daily_run_limit": 10,
                                "monthly_token_limit": 100,
                                "enabled": True,
                            },
                        )
                        ai_applications.save_ai_application(self._sample_ai_application("summarize"))
                        with self.assertRaises(Exception) as raised:
                            ai_applications.save_ai_application(self._sample_ai_application("translate"))
            finally:
                reset_tenant_scope(tenant)

            self.assertIn("quota", str(getattr(raised.exception, "detail", "")).lower())
        finally:
            self._unlink_db(db_path)

    def test_platform_admin_can_configure_ai_application_quota_for_tenant(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                saved = ai_applications.save_tenant_ai_quota(
                    44,
                    {
                        "max_applications": 2,
                        "max_capabilities": 10,
                        "max_assets": 10,
                        "daily_run_limit": 10,
                        "monthly_token_limit": 100,
                        "enabled": True,
                    },
                )
                visible = ai_applications.get_admin_tenant_ai_quota(44)

            self.assertEqual(saved["tenant_id"], 44)
            self.assertEqual(visible["max_applications"], 2)
            self.assertEqual(visible["usage"]["applications"], 0)
        finally:
            self._unlink_db(db_path)

    def test_ai_application_draft_run_records_prompt_trace(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    ai_applications.save_ai_application(self._sample_ai_application("summarize"))

                    def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                        self.assertEqual(kwargs["model"], "dashscope.qwen-plus")
                        messages = kwargs["messages"]
                        assert isinstance(messages, list)
                        self.assertEqual(messages[-1]["content"], "请总结：退款流程是什么")
                        return {
                            "choices": [{"message": {"content": "退款流程摘要"}}],
                            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
                        }

                    with mock.patch(
                        "ai_applications.application.services.gateway.chat_completions",
                        side_effect=fake_chat_completions,
                    ):
                        result = ai_applications.run_draft_application(
                            "summarize",
                            {"variables": {"question": "退款流程是什么"}},
                        )

                    traces = ai_applications.list_prompt_runtime_traces()["items"]

            self.assertEqual(result["answer"], "退款流程摘要")
            self.assertTrue(result["trace_id"].startswith("trace_"))
            self.assertEqual(len(traces), 1)
            self.assertEqual(traces[0]["status"], "success")
            self.assertEqual(traces[0]["input_variables"]["question"], "退款流程是什么")
            self.assertIn("请总结", traces[0]["rendered_prompt"])
        finally:
            self._unlink_db(db_path)

    def test_workflow_sql_node_applies_data_access_scope(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute(
                    """
                    CREATE TABLE workflow_orders (
                        id INTEGER PRIMARY KEY,
                        tenant_id INTEGER NOT NULL,
                        owner_user_id INTEGER NOT NULL,
                        owner_department_id INTEGER,
                        name TEXT NOT NULL,
                        amount INTEGER NOT NULL
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO workflow_orders (tenant_id, owner_user_id, owner_department_id, name, amount) VALUES (?, ?, ?, ?, ?)",
                    (7, 10, 1, "自己的订单", 12),
                )
                conn.execute(
                    "INSERT INTO workflow_orders (tenant_id, owner_user_id, owner_department_id, name, amount) VALUES (?, ?, ?, ?, ?)",
                    (7, 11, 1, "别人的订单", 34),
                )
                conn.commit()
            finally:
                conn.close()

            app = self._sample_ai_application("workflow-sql")
            app["app_type"] = "workflow"
            app["tenant_id"] = 7
            app["runtime_config"] = {
                "workflow": {
                    "nodes": [
                        {"id": "start", "type": "start", "data": {}},
                        {
                            "id": "sql_1",
                            "type": "sql_query",
                            "data": {
                                "sql": "SELECT tenant_id, owner_user_id, owner_department_id, name, amount FROM workflow_orders",
                                "output_key": "records",
                                "data_access": {"resource_key": "workflow.orders"},
                            },
                        },
                        {"id": "end", "type": "end", "data": {"output": "{{records.rows}}"}},
                    ],
                    "edges": [
                        {"source": "start", "target": "sql_1"},
                        {"source": "sql_1", "target": "end"},
                    ],
                }
            }
            current_user = {"id": 10, "tenant_id": 7, "current_tenant": {"id": 7}}

            with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                with mock.patch(
                    "ai_applications.application.services.resolve_data_access_filter",
                    return_value=DataAccessPredicate(tenant_id=7, scope=SCOPE_SELF, user_id=10),
                ):
                    ai_applications.save_ai_application(app, current_user=current_user)
                    result = ai_applications.run_draft_application("workflow-sql", {"variables": {}}, current_user=current_user)

            self.assertIn("自己的订单", result["answer"])
            self.assertNotIn("别人的订单", result["answer"])
            trace_nodes = result["trace"]["rendered_messages"][-1]["content"]["workflow"]["nodes"]
            self.assertEqual(trace_nodes[1]["output"]["row_count"], 1)
        finally:
            self._unlink_db(db_path)

    def test_workflow_sql_node_applies_scope_without_projecting_owner_columns(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute(
                    """
                    CREATE TABLE workflow_orders (
                        id INTEGER PRIMARY KEY,
                        tenant_id INTEGER NOT NULL,
                        owner_user_id INTEGER NOT NULL,
                        owner_department_id INTEGER,
                        name TEXT NOT NULL,
                        amount INTEGER NOT NULL
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO workflow_orders (tenant_id, owner_user_id, owner_department_id, name, amount) VALUES (?, ?, ?, ?, ?)",
                    (7, 10, 1, "自己的订单", 12),
                )
                conn.execute(
                    "INSERT INTO workflow_orders (tenant_id, owner_user_id, owner_department_id, name, amount) VALUES (?, ?, ?, ?, ?)",
                    (7, 11, 1, "别人的订单", 34),
                )
                conn.commit()
            finally:
                conn.close()

            app = self._sample_ai_application("workflow-sql-public-columns")
            app["app_type"] = "workflow"
            app["tenant_id"] = 7
            app["runtime_config"] = {
                "workflow": {
                    "nodes": [
                        {"id": "start", "type": "start", "data": {}},
                        {
                            "id": "sql_1",
                            "type": "sql_query",
                            "data": {
                                "sql": "SELECT name, amount FROM workflow_orders",
                                "output_key": "records",
                                "data_access": {"resource_key": "workflow.orders"},
                            },
                        },
                        {"id": "end", "type": "end", "data": {"output": "{{records.rows}}"}},
                    ],
                    "edges": [
                        {"source": "start", "target": "sql_1"},
                        {"source": "sql_1", "target": "end"},
                    ],
                }
            }
            current_user = {"id": 10, "tenant_id": 7, "current_tenant": {"id": 7}}

            with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                with mock.patch(
                    "ai_applications.application.services.resolve_data_access_filter",
                    return_value=DataAccessPredicate(tenant_id=7, scope=SCOPE_SELF, user_id=10),
                ):
                    ai_applications.save_ai_application(app, current_user=current_user)
                    result = ai_applications.run_draft_application(
                        "workflow-sql-public-columns",
                        {"variables": {}},
                        current_user=current_user,
                    )

            self.assertIn("自己的订单", result["answer"])
            self.assertNotIn("别人的订单", result["answer"])
        finally:
            self._unlink_db(db_path)

    def test_workflow_without_llm_node_does_not_require_model(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            app = self._sample_ai_application("workflow-no-llm")
            app["app_type"] = "workflow"
            app["model_preferences"] = {}
            app["runtime_config"] = {
                "workflow": {
                    "nodes": [
                        {"id": "start", "type": "start", "data": {}},
                        {"id": "end", "type": "end", "data": {"output": "完成"}},
                    ],
                    "edges": [{"source": "start", "target": "end"}],
                }
            }

            with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                ai_applications.save_ai_application(app)
                result = ai_applications.run_draft_application("workflow-no-llm", {"variables": {}})

            self.assertEqual(result["answer"], "完成")
            trace_nodes = result["trace"]["rendered_messages"][-1]["content"]["workflow"]["nodes"]
            self.assertEqual([node["node_id"] for node in trace_nodes], ["start", "end"])
        finally:
            self._unlink_db(db_path)

    def test_workflow_trace_serializes_datetime_values(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            app = self._sample_ai_application("workflow-datetime")
            app["app_type"] = "workflow"
            app["model_preferences"] = {}
            app["runtime_config"] = {
                "workflow": {
                    "nodes": [
                        {"id": "start", "type": "start", "data": {"variables": [{"key": "started_at", "type": "text"}]}},
                        {"id": "end", "type": "end", "data": {"output": "{{started_at}}"}},
                    ],
                    "edges": [{"source": "start", "target": "end"}],
                }
            }
            started_at = datetime(2026, 5, 22, 12, 30, 45)

            with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                ai_applications.save_ai_application(app)
                result = ai_applications.run_draft_application("workflow-datetime", {"variables": {"started_at": started_at}})

            self.assertIn("2026-05-22 12:30:45", result["answer"])
            trace_nodes = result["trace"]["rendered_messages"][-1]["content"]["workflow"]["nodes"]
            self.assertIn("2026-05-22T12:30:45", str(trace_nodes))
        finally:
            self._unlink_db(db_path)

    def test_ai_application_draft_stream_records_prompt_trace(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    ai_applications.save_ai_application(self._sample_ai_application("summarize"))

                    def fake_stream_chat_completions(**kwargs: object) -> object:
                        messages = kwargs["messages"]
                        assert isinstance(messages, list)
                        self.assertEqual(messages[-1]["content"], "请总结：流式输出")
                        yield 'data: {"choices":[{"delta":{"content":"流式"}}]}\n\n'
                        yield 'data: {"choices":[{"delta":{"content":"摘要"}}]}\n\n'
                        yield "data: [DONE]\n\n"

                    with mock.patch(
                        "ai_applications.application.services.gateway.stream_chat_completions",
                        side_effect=fake_stream_chat_completions,
                    ):
                        events = list(
                            ai_applications.stream_draft_application(
                                "summarize",
                                {"variables": {"question": "流式输出"}},
                            )
                        )

                    traces = ai_applications.list_prompt_runtime_traces()["items"]

            self.assertTrue(events[0].startswith("event: meta\n"))
            self.assertIn('"content":"流式"', "".join(events))
            self.assertTrue(any(event.startswith("event: trace\n") for event in events))
            self.assertEqual(events[-1], "data: [DONE]\n\n")
            self.assertEqual(len(traces), 1)
            self.assertEqual(traces[0]["answer"], "流式摘要")
        finally:
            self._unlink_db(db_path)

    def test_ai_application_draft_stream_hides_raw_native_tool_protocol(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    ai_applications.save_ai_application(self._sample_ai_application("tool-protocol-stream"))

                    def fake_stream_chat_completions(**kwargs: object) -> object:
                        yield 'data: {"choices":[{"delta":{"reasoning_content":"I need a file "}}]}\n\n'
                        yield 'data: {"choices":[{"delta":{"reasoning_content":"<tool_call>{\\"name\\":\\"bash\\",\\"arguments\\":{\\"command\\":\\"ls /tmp\\"}}</tool_call>"}}]}\n\n'
                        raise AssertionError("stream should stop before forwarding later chunks")

                    with mock.patch(
                        "ai_applications.application.services.gateway.stream_chat_completions",
                        side_effect=fake_stream_chat_completions,
                    ):
                        events = list(
                            ai_applications.stream_draft_application(
                                "tool-protocol-stream",
                                {"variables": {"question": "read pdf"}, "enable_think_output": True},
                            )
                        )
                    traces = ai_applications.list_prompt_runtime_traces()["items"]

            joined = "".join(events)
            self.assertIn("event: tool_call_blocked", joined)
            self.assertNotIn("<tool_call>", joined)
            self.assertNotIn('"name":"bash"', joined)
            self.assertTrue(joined.rstrip().endswith("data: [DONE]"))
            self.assertEqual(traces[0]["status"], "failed")
            self.assertIn("未被当前流式阶段接管", traces[0]["answer"])
        finally:
            self._unlink_db(db_path)

    def test_single_turn_application_executes_tool_preflight_for_uploaded_files(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        test_case = self

        class FakeSandboxRunner:
            def run(self, request: dict[str, object]) -> dict[str, object]:
                test_case.assertEqual(request["runtime_kind"], "sandbox_python")
                test_case.assertIn("print('quiz ready')", str(request["content"]))
                return {
                    "status": "success",
                    "output": {
                        "stdout": "quiz ready\n",
                        "workspace_files": [{"path": "quiz.html", "content": "<html>quiz</html>"}],
                    },
                }

        previous_runner = ai_applications.skill_runtime._sandbox_runner
        ai_applications.skill_runtime.configure_sandbox_runner(FakeSandboxRunner())
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        ai_applications.save_ai_application(self._sample_ai_application("single-tool"))
                        calls: list[list[dict[str, object]]] = []

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            calls.append(messages)
                            if len(calls) == 1:
                                self.assertIn("Agent execution tools", str(messages[-2]["content"]))
                                return {
                                    "choices": [
                                        {
                                            "message": {
                                                "content": json.dumps(
                                                    {"tool_calls": [{"tool": "python.run", "arguments": {"code": "print('quiz ready')"}}]}
                                                )
                                            }
                                        }
                                    ],
                                    "usage": {"total_tokens": 1},
                                }
                            self.assertIn("quiz.html", str(messages[-1]["content"]))
                            return {"choices": [{"message": {"content": "generated quiz"}}], "usage": {"total_tokens": 2}}

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            result = ai_applications.run_draft_application(
                                "single-tool",
                                {
                                    "variables": {"question": "make quiz"},
                                    "files": [{"name": "content.txt", "mime_type": "text/plain", "text": "lesson"}],
                                },
                            )

            self.assertEqual(result["answer"], "generated quiz")
            self.assertEqual(result["usage"]["total_tokens"], 3)
            self.assertEqual(result["agent_tool_results"][0]["tool"], "python.run")
            self.assertEqual(result["agent_tool_results"][0]["status"], "success")
            self.assertTrue(any("single_turn_" in str(path) for path in workspace_root.rglob("quiz.html")))
        finally:
            ai_applications.skill_runtime.configure_sandbox_runner(previous_runner)
            self._unlink_db(db_path)

    def test_single_turn_stream_emits_agent_tool_result_for_preflight(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)

        class FakeSandboxRunner:
            def run(self, request: dict[str, object]) -> dict[str, object]:
                return {"status": "success", "output": {"stdout": "ready\n"}}

        previous_runner = ai_applications.skill_runtime._sandbox_runner
        ai_applications.skill_runtime.configure_sandbox_runner(FakeSandboxRunner())
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        ai_applications.save_ai_application(self._sample_ai_application("single-stream-tool"))

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            return {
                                "choices": [
                                    {
                                        "message": {
                                            "content": json.dumps(
                                                {"tool_calls": [{"tool": "python.run", "arguments": {"code": "print('ready')"}}]}
                                            )
                                        }
                                    }
                                ],
                                "usage": {},
                            }

                        def fake_stream_chat_completions(**kwargs: object) -> object:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            self.assertIn("Agent tool results", str(messages[-1]["content"]))
                            yield 'data: {"choices":[{"delta":{"content":"final"}}]}\n\n'
                            yield "data: [DONE]\n\n"

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            with mock.patch(
                                "ai_applications.application.services.gateway.stream_chat_completions",
                                side_effect=fake_stream_chat_completions,
                            ):
                                events = list(
                                    ai_applications.stream_draft_application(
                                        "single-stream-tool",
                                        {
                                            "variables": {"question": "make quiz"},
                                            "files": [{"name": "content.txt", "mime_type": "text/plain", "text": "lesson"}],
                                        },
                                    )
                                )

            joined = "".join(events)
            self.assertIn("event: agent_tool_result", joined)
            self.assertIn('"tool": "python.run"', joined)
            self.assertIn('"content":"final"', joined)
            self.assertNotIn("<tool_call>", joined)
        finally:
            ai_applications.skill_runtime.configure_sandbox_runner(previous_runner)
            self._unlink_db(db_path)

    def test_single_turn_stream_blocks_high_risk_tool_preflight(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        ai_applications.save_ai_application(self._sample_ai_application("single-stream-risk"))

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            return {
                                "choices": [
                                    {
                                        "message": {
                                            "content": json.dumps(
                                                {"tool_calls": [{"tool": "shell.run", "arguments": {"command": "rm -rf /"}}]}
                                            )
                                        }
                                    }
                                ],
                                "usage": {},
                            }

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            with mock.patch(
                                "ai_applications.application.services.gateway.stream_chat_completions",
                                side_effect=AssertionError("main stream should not run after high-risk preflight"),
                            ):
                                events = list(
                                    ai_applications.stream_draft_application(
                                        "single-stream-risk",
                                        {
                                            "variables": {"question": "delete everything"},
                                            "files": [{"name": "content.txt", "mime_type": "text/plain", "text": "lesson"}],
                                        },
                                    )
                                )
                        traces = ai_applications.list_prompt_runtime_traces()["items"]

            joined = "".join(events)
            self.assertIn("event: agent_tool_result", joined)
            self.assertIn("AgentToolRiskError", joined)
            self.assertIn("event: tool_call_blocked", joined)
            self.assertIn("风险过高", joined)
            self.assertEqual(traces[0]["status"], "failed")
            self.assertIn("风险过高", traces[0]["answer"])
        finally:
            self._unlink_db(db_path)

    def test_ai_application_draft_stream_records_trace_without_done_event(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    ai_applications.save_ai_application(self._sample_ai_application("summarize"))

                    def fake_stream_chat_completions(**kwargs: object) -> object:
                        messages = kwargs["messages"]
                        assert isinstance(messages, list)
                        self.assertEqual(messages[-1]["content"], "请总结：流自然结束")
                        yield 'data: {"choices":[{"delta":{"content":"自然"}}]}\n\n'
                        yield 'data: {"choices":[{"delta":{"content":"完成"}}]}\n\n'

                    with mock.patch(
                        "ai_applications.application.services.gateway.stream_chat_completions",
                        side_effect=fake_stream_chat_completions,
                    ):
                        events = list(
                            ai_applications.stream_draft_application(
                                "summarize",
                                {"variables": {"question": "流自然结束"}},
                            )
                        )

                    traces = ai_applications.list_prompt_runtime_traces()["items"]
                    logs = ai_applications.list_ai_application_run_logs("summarize")["items"]

            self.assertTrue(any(event.startswith("event: trace\n") for event in events))
            self.assertEqual(events[-1], "data: [DONE]\n\n")
            self.assertEqual(len(traces), 1)
            self.assertEqual(traces[0]["status"], "success")
            self.assertEqual(traces[0]["answer"], "自然完成")
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["answer"], "自然完成")
        finally:
            self._unlink_db(db_path)

    def test_workflow_draft_stream_emits_node_events_before_trace(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    payload = self._sample_ai_application("stream-workflow")
                    payload["app_type"] = "workflow"
                    payload["runtime_config"] = {
                        "workflow": {
                            "nodes": [
                                {"id": "start", "type": "start", "data": {}},
                                {
                                    "id": "llm_1",
                                    "type": "llm",
                                    "data": {
                                        "model": "dashscope.qwen-plus",
                                        "user_prompt_template": "Summarize: {{question}}",
                                    },
                                },
                                {"id": "end", "type": "end", "data": {}},
                            ],
                            "edges": [
                                {"source": "start", "target": "llm_1"},
                                {"source": "llm_1", "target": "end"},
                            ],
                        }
                    }
                    ai_applications.save_ai_application(payload)

                    with mock.patch(
                        "ai_applications.application.services.gateway.chat_completions",
                        return_value={"choices": [{"message": {"content": "workflow answer"}}], "usage": {"total_tokens": 5}},
                    ):
                        events = list(
                            ai_applications.stream_draft_application(
                                "stream-workflow",
                                {"variables": {"question": "node logs"}},
                            )
                        )

                    traces = ai_applications.list_prompt_runtime_traces()["items"]

            joined = "".join(events)
            first_node_index = next(index for index, event in enumerate(events) if event.startswith("event: workflow_node\n"))
            trace_index = next(index for index, event in enumerate(events) if event.startswith("event: trace\n"))
            self.assertLess(first_node_index, trace_index)
            self.assertIn('"event": "workflow.node.started"', joined)
            self.assertIn('"event": "workflow.node.completed"', joined)
            self.assertIn('"node_id": "llm_1"', joined)
            self.assertEqual(events[-1], "data: [DONE]\n\n")
            self.assertEqual(traces[0]["answer"], "workflow answer")
        finally:
            self._unlink_db(db_path)

    def test_ai_application_run_logs_are_scoped_to_application(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    ai_applications.save_ai_application(self._sample_ai_application("summarize"))
                    ai_applications.save_ai_application(self._sample_ai_application("translate"))

                    def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                        messages = kwargs["messages"]
                        assert isinstance(messages, list)
                        return {"choices": [{"message": {"content": str(messages[-1]["content"])}}], "usage": {}}

                    with mock.patch(
                        "ai_applications.application.services.gateway.chat_completions",
                        side_effect=fake_chat_completions,
                    ):
                        ai_applications.run_draft_application("summarize", {"variables": {"question": "A"}})
                        ai_applications.run_draft_application("translate", {"variables": {"question": "B"}})

                    logs = ai_applications.list_ai_application_run_logs("summarize")["items"]

            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["app_key"], "summarize")
            self.assertEqual(logs[0]["run_mode"], "studio_draft")
            self.assertTrue(logs[0]["run_id"].startswith("trace_"))
        finally:
            self._unlink_db(db_path)

    def test_prompt_asset_reference_checker_finds_ai_application_usage(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    app_payload = self._sample_ai_application("summarize")
                    app_payload["runtime_config"] = {
                        **app_payload.get("runtime_config", {}),
                        "system_prompt_source": "asset",
                        "system_prompt_asset_key": "meeting.summary",
                    }
                    ai_applications.save_ai_application(app_payload)

                    referenced = ai_applications.prompt_asset_is_referenced(
                        tenant_id=1,
                        prompt_key="meeting.summary",
                    )
                    unrelated = ai_applications.prompt_asset_is_referenced(
                        tenant_id=1,
                        prompt_key="other.prompt",
                    )

            self.assertTrue(referenced)
            self.assertFalse(unrelated)
        finally:
            self._unlink_db(db_path)

    def test_ai_application_multimodal_variable_renders_openai_content_parts(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    app_payload = self._sample_ai_application("vision")
                    app_payload["user_prompt_template"] = "请分析图片：{{image}}"
                    app_payload["variables_schema"] = {
                        "type": "object",
                        "required": ["image"],
                        "properties": {"image": {"type": "image"}},
                    }
                    ai_applications.save_ai_application(app_payload)

                    def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                        messages = kwargs["messages"]
                        assert isinstance(messages, list)
                        content = messages[-1]["content"]
                        assert isinstance(content, list)
                        self.assertEqual(content[0]["type"], "text")
                        self.assertIn("已上传image", content[0]["text"])
                        self.assertEqual(content[1]["type"], "image_url")
                        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
                        return {"choices": [{"message": {"content": "图片里有一个按钮"}}], "usage": {}}

                    with mock.patch(
                        "ai_applications.application.services.gateway.chat_completions",
                        side_effect=fake_chat_completions,
                    ):
                        result = ai_applications.run_draft_application(
                            "vision",
                            {
                                "variables": {
                                    "image": {
                                        "type": "image",
                                        "name": "screen.png",
                                        "mime_type": "image/png",
                                        "size": 12,
                                        "data_url": self._image_data_url(width=1600, height=900),
                                    }
                                }
                            },
                        )

            self.assertEqual(result["answer"], "图片里有一个按钮")
            self.assertIn("[image]", result["trace"]["rendered_prompt"])
            self.assertNotIn("iVBORw0KGgo", json.dumps(result["trace"], ensure_ascii=False))
        finally:
            self._unlink_db(db_path)

    def test_ai_application_image_variable_accepts_multiple_images(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    app_payload = self._sample_ai_application("vision-gallery")
                    app_payload["user_prompt_template"] = "请分析图片：{{images}}"
                    app_payload["variables_schema"] = {
                        "type": "object",
                        "required": ["images"],
                        "properties": {"images": {"type": "image"}},
                    }
                    ai_applications.save_ai_application(app_payload)

                    def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                        messages = kwargs["messages"]
                        assert isinstance(messages, list)
                        content = messages[-1]["content"]
                        assert isinstance(content, list)
                        self.assertEqual([part["type"] for part in content], ["text", "image_url", "image_url"])
                        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
                        self.assertTrue(content[2]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
                        return {"choices": [{"message": {"content": "两张图片已分析"}}], "usage": {}}

                    with mock.patch(
                        "ai_applications.application.services.gateway.chat_completions",
                        side_effect=fake_chat_completions,
                    ):
                        result = ai_applications.run_draft_application(
                            "vision-gallery",
                            {
                                "variables": {
                                    "images": [
                                        {
                                            "type": "image",
                                            "name": "screen-1.png",
                                            "mime_type": "image/png",
                                            "size": 12,
                                            "data_url": self._image_data_url(width=1600, height=900, color=(220, 30, 30)),
                                        },
                                        {
                                            "type": "image",
                                            "name": "screen-2.png",
                                            "mime_type": "image/png",
                                            "size": 13,
                                            "data_url": self._image_data_url(width=1400, height=800, color=(30, 30, 220)),
                                        },
                                    ]
                                }
                            },
                        )

                    trace_detail = ai_applications.get_prompt_runtime_trace(result["trace_id"])

            self.assertEqual(result["answer"], "两张图片已分析")
            self.assertIn("[image]", result["trace"]["rendered_prompt"])
            self.assertNotIn("iVBORw0KGgo", json.dumps(trace_detail, ensure_ascii=False))
        finally:
            self._unlink_db(db_path)

    def test_ai_application_multimodal_trace_redacts_binary_payloads_in_storage(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    app_payload = self._sample_ai_application("vision")
                    app_payload["user_prompt_template"] = "请分析图片：{{image}}"
                    app_payload["variables_schema"] = {
                        "type": "object",
                        "required": ["image"],
                        "properties": {"image": {"type": "image"}},
                    }
                    ai_applications.save_ai_application(app_payload)

                    with mock.patch(
                        "ai_applications.application.services.gateway.chat_completions",
                        return_value={"choices": [{"message": {"content": "图片分析完成"}}], "usage": {}},
                    ):
                        result = ai_applications.run_draft_application(
                            "vision",
                            {
                                "variables": {
                                    "image": {
                                        "type": "image",
                                        "name": "screen.png",
                                        "mime_type": "image/png",
                                        "size": 12,
                                        "data_url": self._image_data_url(width=1600, height=900),
                                    }
                                }
                            },
                        )

                    traces = ai_applications.list_prompt_runtime_traces()["items"]
                    trace_detail = ai_applications.get_prompt_runtime_trace(result["trace_id"])

            self.assertEqual(len(traces), 1)
            self.assertEqual(traces[0]["input_variables"]["image"]["name"], "screen.png")
            self.assertTrue(traces[0]["input_variables"]["image"]["redacted"])
            self.assertNotIn("iVBORw0KGgo", json.dumps(traces[0], ensure_ascii=False))
            self.assertNotIn("iVBORw0KGgo", json.dumps(trace_detail, ensure_ascii=False))
        finally:
            self._unlink_db(db_path)

    def test_ai_application_audio_and_video_variables_render_multimodal_parts(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    app_payload = self._sample_ai_application("media")
                    app_payload["user_prompt_template"] = "请分析媒体：{{audio}} {{video}}"
                    app_payload["variables_schema"] = {
                        "type": "object",
                        "required": ["audio", "video"],
                        "properties": {"audio": {"type": "audio"}, "video": {"type": "video"}},
                    }
                    ai_applications.save_ai_application(app_payload)

                    def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                        messages = kwargs["messages"]
                        assert isinstance(messages, list)
                        content = messages[-1]["content"]
                        assert isinstance(content, list)
                        self.assertEqual([part["type"] for part in content], ["text", "input_audio", "video_url"])
                        self.assertEqual(content[1]["input_audio"]["data"], "abc")
                        self.assertEqual(content[1]["input_audio"]["format"], "mpeg")
                        self.assertEqual(content[2]["video_url"]["url"], "data:video/mp4;base64,def")
                        return {"choices": [{"message": {"content": "媒体分析完成"}}], "usage": {}}

                    with mock.patch(
                        "ai_applications.application.services.gateway.chat_completions",
                        side_effect=fake_chat_completions,
                    ):
                        result = ai_applications.run_draft_application(
                            "media",
                            {
                                "variables": {
                                    "audio": {
                                        "type": "audio",
                                        "name": "meeting.mp3",
                                        "mime_type": "audio/mpeg",
                                        "size": 12,
                                        "data_url": "data:audio/mpeg;base64,abc",
                                    },
                                    "video": {
                                        "type": "video",
                                        "name": "demo.mp4",
                                        "mime_type": "video/mp4",
                                        "size": 24,
                                        "data_url": "data:video/mp4;base64,def",
                                    },
                                }
                            },
                        )

            self.assertEqual(result["answer"], "媒体分析完成")
            self.assertIn("[audio]", result["trace"]["rendered_prompt"])
            self.assertIn("[video]", result["trace"]["rendered_prompt"])
        finally:
            self._unlink_db(db_path)

    def test_ai_application_file_variable_stays_text_placeholder_for_now(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    app_payload = self._sample_ai_application("file-only")
                    app_payload["user_prompt_template"] = "请查看附件：{{attachment}}"
                    app_payload["variables_schema"] = {
                        "type": "object",
                        "required": ["attachment"],
                        "properties": {"attachment": {"type": "file"}},
                    }
                    ai_applications.save_ai_application(app_payload)

                    def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                        messages = kwargs["messages"]
                        assert isinstance(messages, list)
                        content = messages[-1]["content"]
                        assert isinstance(content, str)
                        self.assertIn("已上传file", content)
                        self.assertNotIn("file_data", content)
                        return {"choices": [{"message": {"content": "请提供文件文本内容"}}], "usage": {}}

                    with mock.patch(
                        "ai_applications.application.services.gateway.chat_completions",
                        side_effect=fake_chat_completions,
                    ):
                        result = ai_applications.run_draft_application(
                            "file-only",
                            {
                                "variables": {
                                    "attachment": {
                                        "type": "file",
                                        "name": "report.pdf",
                                        "mime_type": "application/pdf",
                                        "size": 24,
                                        "data_url": "data:application/pdf;base64,abc",
                                    }
                                }
                            },
                        )

            self.assertEqual(result["answer"], "请提供文件文本内容")
        finally:
            self._unlink_db(db_path)

    def test_chat_route_falls_back_when_text_client_receives_multimodal_messages(self) -> None:
        db_path = self._temporary_db_path()
        sqlite3.connect(db_path).close()
        try:
            self._seed_route(db_path)
            calls: list[str] = []

            def fake_client_for_entry(entry: object, *, response_format: str | None = None) -> object:
                model_key = str(getattr(entry, "model_key"))
                calls.append(model_key)

                if model_key == "dashscope.qwen-plus":
                    class TextClient:
                        def generate_response(self, prompt: str, *, enable_think_output: bool | None = None) -> LLMResponse:
                            return LLMResponse(content="text only", elapsed_seconds=0.01)

                    return TextClient()

                class ChatClient:
                    def generate_chat_response(
                        self_client,
                        messages: list[dict[str, object]],
                        *,
                        extra_body: dict[str, object] | None = None,
                        enable_think_output: bool | None = None,
                    ) -> LLMResponse:
                        content = messages[-1]["content"]
                        assert isinstance(content, list)
                        self.assertEqual(content[1]["type"], "input_audio")
                        return LLMResponse(content="audio accepted", elapsed_seconds=0.02)

                return ChatClient()

            with mock.patch("llm_runtime.application.gateway.client_for_entry", side_effect=fake_client_for_entry):
                response = gateway.chat_completions(
                    model="ops.sample.rank",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "请转写"},
                                {"type": "input_audio", "input_audio": {"data": "abc", "format": "mp3"}},
                            ],
                        }
                    ],
                    database_target_override=db_path,
                )

            self.assertEqual(response["choices"][0]["message"]["content"], "audio accepted")
            self.assertEqual(calls, ["dashscope.qwen-plus", "siliconflow.qwen3-32b"])
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                logs = [dict(row) for row in conn.execute("SELECT * FROM llm_call_logs ORDER BY id").fetchall()]
            finally:
                conn.close()
            self.assertEqual([item["status"] for item in logs], ["failed", "success"])
            self.assertEqual(logs[1]["is_fallback"], 1)
        finally:
            self._unlink_db(db_path)

    def test_ai_application_replaces_numeric_template_variable_names(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    app_payload = self._sample_ai_application("numeric_var")
                    app_payload["user_prompt_template"] = "会议内容：{{11}}"
                    app_payload["variables_schema"] = {
                        "type": "object",
                        "required": ["11"],
                        "properties": {"11": {"type": "string", "label": "会议内容"}},
                    }
                    ai_applications.save_ai_application(app_payload)

                    def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                        messages = kwargs["messages"]
                        assert isinstance(messages, list)
                        self.assertIn("会议内容：邓柯炳发言", messages[-1]["content"])
                        return {"choices": [{"message": {"content": "已解析变量"}}], "usage": {}}

                    with mock.patch(
                        "ai_applications.application.services.gateway.chat_completions",
                        side_effect=fake_chat_completions,
                    ):
                        result = ai_applications.run_draft_application(
                            "numeric_var",
                            {"variables": {"11": "邓柯炳发言"}},
                        )

            self.assertEqual(result["answer"], "已解析变量")
            self.assertIn("会议内容：邓柯炳发言", result["trace"]["rendered_prompt"])
            self.assertNotIn("{{11}}", result["trace"]["rendered_prompt"])
        finally:
            self._unlink_db(db_path)

    def test_ai_application_can_resolve_system_prompt_from_published_prompt_asset(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        self._initialize_ai_assets_db(db_path)
        current_user = {
            "id": 10,
            "username": "owner",
            "current_tenant": {"id": 1, "tenant_key": "default", "name": "Default"},
            "tenant_id": 1,
        }
        try:
            tenant = set_tenant_scope(TenantScope(tenant_id=1, tenant_key="default", tenant_name="Default"))
            try:
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        with mock.patch("ai_assets.infrastructure.persistence.repositories.resolve_db_path", return_value=db_path):
                            prompt = ai_asset_services.save_prompt_asset(
                                {
                                    "prompt_key": "support.system",
                                    "name": "Support System",
                                    "description": "",
                                    "tags": [],
                                    "status": "draft",
                                },
                                current_user,
                            )["item"]
                            version = ai_asset_services.save_prompt_version(
                                int(prompt["id"]),
                                {
                                    "version": "v2",
                                    "system_prompt": "你是退款专家，只回答退款流程。",
                                    "developer_prompt": "",
                                    "user_prompt_template": "",
                                    "variables_schema": {},
                                    "output_schema": {},
                                    "render_engine": "simple",
                                    "status": "draft",
                                },
                                current_user,
                            )["item"]
                            ai_asset_services.publish_prompt_version(int(prompt["id"]), int(version["id"]), current_user)

                            app_payload = self._sample_ai_application("summarize")
                            app_payload["system_prompt"] = "inline fallback"
                            app_payload["runtime_config"] = {
                                "system_prompt_source": "asset",
                                "system_prompt_asset_key": "support.system",
                            }
                            ai_applications.save_ai_application(app_payload)

                            def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                                messages = kwargs["messages"]
                                assert isinstance(messages, list)
                                self.assertEqual(messages[0]["role"], "system")
                                self.assertEqual(messages[0]["content"], "你是退款专家，只回答退款流程。")
                                return {"choices": [{"message": {"content": "退款流程摘要"}}], "usage": {}}

                            with mock.patch(
                                "ai_applications.application.services.gateway.chat_completions",
                                side_effect=fake_chat_completions,
                            ):
                                result = ai_applications.run_draft_application(
                                    "summarize",
                                    {"variables": {"question": "怎么退款"}},
                                )

                            trace = result["trace"]
            finally:
                reset_tenant_scope(tenant)

            self.assertEqual(result["answer"], "退款流程摘要")
            self.assertEqual(trace["rendered_messages"][0]["prompt_source"], "prompt_asset")
            self.assertEqual(trace["rendered_messages"][0]["prompt_asset_key"], "support.system")
            self.assertEqual(trace["rendered_messages"][0]["prompt_version"], "v2")
        finally:
            self._unlink_db(db_path)

    def test_unpublished_ai_application_cannot_run_external_api(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    ai_applications.save_ai_application(self._sample_ai_application("summarize"))
                    with self.assertRaises(Exception) as raised:
                        ai_applications.run_published_application("summarize", {"variables": {"question": "hello"}})

            self.assertIn("not published", str(getattr(raised.exception, "detail", "")))
        finally:
            self._unlink_db(db_path)

    def test_agent_application_runs_multi_turn_conversation(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    payload = self._sample_ai_application("support-agent")
                    payload["app_type"] = "agent"
                    payload["system_prompt"] = "你是客服 Agent"
                    payload["user_prompt_template"] = ""
                    payload["variables_schema"] = {}
                    ai_applications.save_ai_application(payload)
                    conversation = ai_applications.create_agent_conversation("support-agent", {"title": "退款咨询"})

                    calls: list[list[dict[str, object]]] = []

                    def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                        messages = kwargs["messages"]
                        assert isinstance(messages, list)
                        calls.append(messages)
                        return {"choices": [{"message": {"content": f"answer-{len(calls)}"}}], "usage": {}}

                    with mock.patch(
                        "ai_applications.application.services.gateway.chat_completions",
                        side_effect=fake_chat_completions,
                    ):
                        first = ai_applications.send_agent_message(
                            "support-agent",
                            conversation["conversation_key"],
                            {"content": "第一问", "variables": {}},
                        )
                        second = ai_applications.send_agent_message(
                            "support-agent",
                            conversation["conversation_key"],
                            {"content": "第二问", "variables": {}},
                        )
                    messages = ai_applications.list_agent_messages("support-agent", conversation["conversation_key"])["items"]

            self.assertEqual(first["assistant_message"]["content"], "answer-1")
            self.assertEqual(second["assistant_message"]["content"], "answer-2")
            self.assertEqual([item["role"] for item in calls[1][-3:]], ["user", "assistant", "user"])
            self.assertEqual([item["content"] for item in calls[1][-3:]], ["第一问", "answer-1", "第二问"])
            self.assertEqual([item["role"] for item in messages], ["user", "assistant", "user", "assistant"])
        finally:
            self._unlink_db(db_path)

    def test_agent_application_executes_default_file_tools(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("file-agent")
                        payload["app_type"] = "agent"
                        payload["system_prompt"] = "You are a file-capable agent."
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("file-agent", {"title": "files"})

                        calls: list[list[dict[str, object]]] = []

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            calls.append(messages)
                            if len(calls) == 1:
                                self.assertIn("Agent file workspace tools", str(messages[-2]["content"]))
                                return {
                                    "choices": [
                                        {
                                            "message": {
                                                "content": json.dumps(
                                                    {
                                                        "tool_calls": [
                                                            {
                                                                "tool": "write_file",
                                                                "arguments": {"path": "notes/todo.txt", "content": "hello file", "overwrite": True},
                                                            },
                                                            {"tool": "read_file", "arguments": {"path": "notes/todo.txt"}},
                                                        ]
                                                    }
                                                )
                                            }
                                        }
                                    ],
                                    "usage": {"total_tokens": 2},
                                }
                            self.assertIn("Agent tool results", str(messages[-1]["content"]))
                            return {"choices": [{"message": {"content": "file is ready"}}], "usage": {"total_tokens": 3}}

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            result = ai_applications.send_agent_message(
                                "file-agent",
                                conversation["conversation_key"],
                                {
                                    "content": "write and read a file",
                                    "variables": {},
                                    "files": [{"name": "source.txt", "type": "file", "mime_type": "text/plain", "text": "uploaded text"}],
                                },
                            )
                        messages = ai_applications.list_agent_messages("file-agent", conversation["conversation_key"])["items"]

            self.assertEqual(result["answer"], "file is ready")
            self.assertEqual(result["usage"]["total_tokens"], 5)
            self.assertEqual([item["status"] for item in result["agent_tool_results"]], ["success", "success"])
            self.assertEqual(result["agent_tool_results"][1]["output"]["content"], "hello file")
            self.assertTrue((workspace_root / "tenant_1" / "file-agent" / conversation["conversation_key"] / "notes" / "todo.txt").exists())
            self.assertTrue(any(item["role"] == "tool" and item["metadata"].get("agent_file_tool_results") for item in messages))
            self.assertEqual(result["agent_file_workspace"]["uploads"][0]["path"], "uploads/source.txt")
        finally:
            self._unlink_db(db_path)

    def test_agent_application_executes_shell_tool_through_sandbox(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        test_case = self

        class FakeSandboxRunner:
            def run(self, request: dict[str, object]) -> dict[str, object]:
                self_request = request
                test_case.assertEqual(self_request["runtime_kind"], "sandbox_shell")
                test_case.assertEqual(self_request["content"], "cat uploads/source.txt > result.txt")
                workspace_files = self_request.get("workspace_files")
                test_case.assertIsInstance(workspace_files, list)
                test_case.assertTrue(any(item.get("path") == "uploads/source.txt" for item in workspace_files if isinstance(item, dict)))
                return {
                    "status": "success",
                    "output": {
                        "stdout": "",
                        "stderr": "",
                        "returncode": 0,
                        "workspace_files": [{"path": "result.txt", "content": "copied text"}],
                    },
                }

        self_runner = FakeSandboxRunner()
        previous_runner = ai_applications.skill_runtime._sandbox_runner
        ai_applications.skill_runtime.configure_sandbox_runner(self_runner)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("shell-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("shell-agent", {"title": "shell"})

                        calls: list[list[dict[str, object]]] = []

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            calls.append(messages)
                            if len(calls) == 1:
                                return {
                                    "choices": [
                                        {
                                            "message": {
                                                "content": '<tool_call>{"name":"bash","arguments":{"cmd":"cat uploads/source.txt > result.txt"}}</tool_call>'
                                            }
                                        }
                                    ],
                                    "usage": {"total_tokens": 1},
                                }
                            self.assertIn("shell.run", str(messages[-1]["content"]))
                            self.assertIn("copied text", str(messages[-1]["content"]))
                            return {"choices": [{"message": {"content": "shell done"}}], "usage": {"total_tokens": 2}}

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            result = ai_applications.send_agent_message(
                                "shell-agent",
                                conversation["conversation_key"],
                                {
                                    "content": "copy uploaded text",
                                    "variables": {},
                                    "files": [{"name": "source.txt", "mime_type": "text/plain", "text": "uploaded text"}],
                                },
                            )

            self.assertEqual(result["answer"], "shell done")
            self.assertEqual(result["trace"]["status"], "success")
            self.assertEqual(result["agent_tool_results"][0]["tool"], "shell.run")
            self.assertEqual(result["agent_tool_results"][0]["status"], "success")
            result_path = workspace_root / "tenant_1" / "shell-agent" / conversation["conversation_key"] / "result.txt"
            self.assertEqual(result_path.read_text(encoding="utf-8"), "copied text")
        finally:
            ai_applications.skill_runtime.configure_sandbox_runner(previous_runner)
            self._unlink_db(db_path)

    def test_agent_application_executes_python_tool_through_sandbox(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        test_case = self

        class FakeSandboxRunner:
            def run(self, request: dict[str, object]) -> dict[str, object]:
                test_case.assertEqual(request["runtime_kind"], "sandbox_python")
                test_case.assertIn("print(1 + 1)", str(request["content"]))
                return {"status": "success", "output": {"stdout": "2\n"}}

        previous_runner = ai_applications.skill_runtime._sandbox_runner
        ai_applications.skill_runtime.configure_sandbox_runner(FakeSandboxRunner())
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("python-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("python-agent", {"title": "python"})

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            if len(messages) < 4:
                                return {
                                    "choices": [
                                        {
                                            "message": {
                                                "content": json.dumps(
                                                    {"tool_calls": [{"tool": "python.run", "arguments": {"code": "print(1 + 1)"}}]}
                                                )
                                            }
                                        }
                                    ],
                                    "usage": {},
                                }
                            self.assertIn("2", str(messages[-1]["content"]))
                            return {"choices": [{"message": {"content": "python done"}}], "usage": {}}

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            result = ai_applications.send_agent_message(
                                "python-agent",
                                conversation["conversation_key"],
                                {"content": "calculate", "variables": {}},
                            )

            self.assertEqual(result["answer"], "python done")
            self.assertEqual(result["agent_tool_results"][0]["tool"], "python.run")
            self.assertEqual(result["agent_tool_results"][0]["output"]["stdout"], "2\n")
        finally:
            ai_applications.skill_runtime.configure_sandbox_runner(previous_runner)
            self._unlink_db(db_path)

    def test_agent_file_tools_reject_workspace_escape(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("safe-file-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("safe-file-agent", {"title": "safe"})

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            if len(messages) < 4:
                                return {
                                    "choices": [
                                        {
                                            "message": {
                                                "content": json.dumps(
                                                    {
                                                        "tool_calls": [
                                                            {
                                                                "tool": "write_file",
                                                                "arguments": {"path": "../secret.txt", "content": "nope"},
                                                            }
                                                        ]
                                                    }
                                                )
                                            }
                                        }
                                    ],
                                    "usage": {},
                                }
                            self.assertIn("parent path segments are not allowed", str(messages[-1]["content"]))
                            return {"choices": [{"message": {"content": "blocked"}}], "usage": {}}

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            result = ai_applications.send_agent_message(
                                "safe-file-agent",
                                conversation["conversation_key"],
                                {"content": "write file outside workspace", "variables": {}},
                            )

            self.assertEqual(result["answer"], "blocked")
            self.assertEqual(result["agent_tool_results"][0]["status"], "failed")
            self.assertEqual(result["agent_tool_results"][0]["error_code"], "AgentFileToolError")
            self.assertFalse((workspace_root / "tenant_1" / "secret.txt").exists())
        finally:
            self._unlink_db(db_path)

    def test_agent_message_reports_shell_tool_failure_when_sandbox_unavailable(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("native-tool-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("native-tool-agent", {"title": "native-tool"})

                        calls: list[list[dict[str, object]]] = []

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            calls.append(messages)
                            if len(calls) > 1:
                                self.assertIn("SkillRuntimeError", str(messages[-1]["content"]))
                                return {"choices": [{"message": {"content": "sandbox unavailable"}}], "usage": {}}
                            return {
                                "choices": [
                                    {
                                        "message": {
                                            "content": '<tool_call>{"name":"bash","arguments":{"cmd":"cat uploads/a.log"}}</tool_call>'
                                        }
                                    }
                                ],
                                "usage": {"total_tokens": 9},
                            }

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            result = ai_applications.send_agent_message(
                                "native-tool-agent",
                                conversation["conversation_key"],
                                {"content": "read logs", "variables": {}},
                            )
                        messages = ai_applications.list_agent_messages("native-tool-agent", conversation["conversation_key"])["items"]

            self.assertIn("sandbox", result["answer"].lower())
            self.assertEqual(result["assistant_message"]["status"], "completed")
            self.assertEqual(result["trace"]["status"], "success")
            self.assertEqual(result["usage"]["total_tokens"], 9)
            self.assertEqual(result["agent_tool_results"][0]["tool"], "shell.run")
            self.assertEqual(result["agent_tool_results"][0]["status"], "failed")
            self.assertEqual(result["agent_tool_results"][0]["error_code"], "SkillRuntimeError")
            self.assertTrue(any(item["role"] == "tool" and item["status"] == "failed" for item in messages))
        finally:
            self._unlink_db(db_path)

    def test_agent_message_blocks_high_risk_shell_tool_without_followup(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("risk-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("risk-agent", {"title": "risk"})

                        calls: list[list[dict[str, object]]] = []

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            calls.append(messages)
                            return {
                                "choices": [
                                    {
                                        "message": {
                                            "content": json.dumps(
                                                {"tool_calls": [{"tool": "shell.run", "arguments": {"command": "rm -rf /"}}]}
                                            )
                                        }
                                    }
                                ],
                                "usage": {"total_tokens": 4},
                            }

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            result = ai_applications.send_agent_message(
                                "risk-agent",
                                conversation["conversation_key"],
                                {"content": "delete everything", "variables": {}},
                            )
                        messages = ai_applications.list_agent_messages("risk-agent", conversation["conversation_key"])["items"]

            self.assertEqual(len(calls), 1)
            self.assertEqual(result["assistant_message"]["status"], "failed")
            self.assertEqual(result["trace"]["status"], "failed")
            self.assertIn("风险过高", result["answer"])
            self.assertEqual(result["agent_tool_results"][0]["tool"], "shell.run")
            self.assertEqual(result["agent_tool_results"][0]["status"], "failed")
            self.assertEqual(result["agent_tool_results"][0]["error_code"], "AgentToolRiskError")
            self.assertEqual(result["agent_tool_results"][0]["risk"]["level"], "high")
            tool_messages = [item for item in messages if item["role"] == "tool"]
            self.assertEqual(tool_messages[-1]["status"], "failed")
        finally:
            self._unlink_db(db_path)

    def test_agent_message_fails_when_model_asks_for_solo_confirmation(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("confirm-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("confirm-agent", {"title": "confirm"})

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            return_value={"choices": [{"message": {"content": "请确认是否执行这个 shell 命令？"}}], "usage": {}},
                        ):
                            result = ai_applications.send_agent_message(
                                "confirm-agent",
                                conversation["conversation_key"],
                                {"content": "run it", "variables": {}},
                            )

            self.assertEqual(result["assistant_message"]["status"], "failed")
            self.assertEqual(result["trace"]["status"], "failed")
            self.assertIn("Solo 模式不支持用户确认式工具调用", result["answer"])
            self.assertEqual(result["agent_tool_results"], [])
        finally:
            self._unlink_db(db_path)

    def test_agent_message_treats_plain_python_json_as_tool_request(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("python-text-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("python-text-agent", {"title": "python-text"})

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            return {
                                "choices": [
                                    {
                                        "message": {
                                            "content": '{"name":"python","arguments":{"code":"print(1)"}}'
                                        }
                                    }
                                ],
                                "usage": {},
                            }

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            result = ai_applications.send_agent_message(
                                "python-text-agent",
                                conversation["conversation_key"],
                                {"content": "show python example", "variables": {}},
                            )

            self.assertEqual(result["assistant_message"]["status"], "failed")
            self.assertEqual(result["trace"]["status"], "failed")
            self.assertEqual(result["agent_tool_results"][0]["tool"], "python.run")
            self.assertEqual(result["agent_tool_results"][0]["status"], "failed")
            self.assertIn("未被当前流式阶段接管", result["answer"])
        finally:
            self._unlink_db(db_path)

    def test_stream_agent_message_executes_file_tool_preflight(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("stream-file-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("stream-file-agent", {"title": "stream-files"})

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            self.assertEqual(kwargs.get("response_format"), {"type": "json_object"})
                            return {
                                "choices": [
                                    {
                                        "message": {
                                            "content": json.dumps(
                                                {
                                                    "tool_calls": [
                                                        {
                                                            "tool": "write_file",
                                                            "arguments": {"path": "stream.txt", "content": "stream content"},
                                                        }
                                                    ]
                                                }
                                            )
                                        }
                                    }
                                ],
                                "usage": {},
                            }

                        def fake_stream_chat_completions_after_failed_tool(**kwargs: object) -> object:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            self.assertIn("SkillRuntimeError", str(messages[-1]["content"]))
                            yield 'data: {"choices":[{"delta":{"content":"sandbox unavailable"}}]}\n\n'
                            yield "data: [DONE]\n\n"

                        def fake_stream_chat_completions(**kwargs: object) -> object:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            self.assertIn("Agent tool results", str(messages[-1]["content"]))
                            yield 'data: {"choices":[{"delta":{"content":"stream "}}]}\n\n'
                            yield 'data: {"choices":[{"delta":{"content":"done"}}]}\n\n'
                            yield "data: [DONE]\n\n"

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            with mock.patch(
                                "ai_applications.application.services.gateway.stream_chat_completions",
                                side_effect=fake_stream_chat_completions,
                            ):
                                events = list(
                                    ai_applications.stream_agent_message(
                                        "stream-file-agent",
                                        conversation["conversation_key"],
                                        {"content": "write file stream.txt", "variables": {}},
                                    )
                                )
                        messages = ai_applications.list_agent_messages("stream-file-agent", conversation["conversation_key"])["items"]

            self.assertTrue(any(event.startswith("event: agent_tool_result\n") for event in events))
            self.assertIn('"content":"stream "', "".join(events))
            self.assertTrue((workspace_root / "tenant_1" / "stream-file-agent" / conversation["conversation_key"] / "stream.txt").exists())
            assistant_messages = [item for item in messages if item["role"] == "assistant"]
            self.assertEqual(assistant_messages[-1]["content"], "stream done")
            self.assertTrue(any(item["role"] == "tool" and item["metadata"].get("agent_file_tool_results") for item in messages))
        finally:
            self._unlink_db(db_path)

    def test_stream_agent_message_reports_shell_tool_failure_when_sandbox_unavailable(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("stream-boundary-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("stream-boundary-agent", {"title": "boundary"})

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            self.assertEqual(kwargs.get("response_format"), {"type": "json_object"})
                            return {
                                "choices": [
                                    {
                                        "message": {
                                            "content": '1<]minimax[>|<tool_call>{"name":"bash","arguments":{"cmd":"find ."}}|</tool_call>'
                                        }
                                    }
                                ],
                                "usage": {},
                            }

                        def fake_stream_chat_completions_after_failed_tool(**kwargs: object) -> object:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            self.assertIn("SkillRuntimeError", str(messages[-1]["content"]))
                            yield 'data: {"choices":[{"delta":{"content":"sandbox unavailable"}}]}\n\n'
                            yield "data: [DONE]\n\n"

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            with mock.patch(
                                "ai_applications.application.services.gateway.stream_chat_completions",
                                side_effect=fake_stream_chat_completions_after_failed_tool,
                            ):
                                events = list(
                                    ai_applications.stream_agent_message(
                                        "stream-boundary-agent",
                                        conversation["conversation_key"],
                                        {"content": "分析日志压缩包", "variables": {}},
                                    )
                                )
                        messages = ai_applications.list_agent_messages("stream-boundary-agent", conversation["conversation_key"])["items"]

            joined = "".join(events)
            self.assertIn("event: agent_tool_result", joined)
            self.assertIn("SkillRuntimeError", joined)
            self.assertTrue(any(event.startswith("event: final\n") for event in events))
            assistant_messages = [item for item in messages if item["role"] == "assistant"]
            self.assertEqual(assistant_messages[-1]["status"], "completed")
            self.assertIn("sandbox unavailable", assistant_messages[-1]["content"])
            tool_messages = [item for item in messages if item["role"] == "tool"]
            self.assertEqual(tool_messages[-1]["status"], "failed")
            self.assertEqual(tool_messages[-1]["metadata"]["agent_tool_results"][0]["error_code"], "SkillRuntimeError")
        finally:
            self._unlink_db(db_path)

    def test_stream_agent_message_reports_run_command_tool_failure_when_sandbox_unavailable(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("stream-run-command-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("stream-run-command-agent", {"title": "run-command"})

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            return {
                                "choices": [
                                    {
                                        "message": {
                                            "content": (
                                                '<tool_call>{"name":"run_command","arguments":{"command":"pdftotext file.pdf /tmp/document.txt"}}</tool_call>'
                                                '<tool_result>{"result":"undefined name pdftotext"}</tool_result>'
                                            )
                                        }
                                    }
                                ],
                                "usage": {},
                            }

                        def fake_stream_chat_completions_after_failed_tool(**kwargs: object) -> object:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            self.assertIn("SkillRuntimeError", str(messages[-1]["content"]))
                            yield 'data: {"choices":[{"delta":{"content":"sandbox unavailable"}}]}\n\n'
                            yield "data: [DONE]\n\n"

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            with mock.patch(
                                "ai_applications.application.services.gateway.stream_chat_completions",
                                side_effect=fake_stream_chat_completions_after_failed_tool,
                            ):
                                events = list(
                                    ai_applications.stream_agent_message(
                                        "stream-run-command-agent",
                                        conversation["conversation_key"],
                                        {"content": "generate quiz from pdf", "variables": {}},
                                    )
                                )
                        messages = ai_applications.list_agent_messages("stream-run-command-agent", conversation["conversation_key"])["items"]

            joined = "".join(events)
            self.assertIn("event: agent_tool_result", joined)
            self.assertIn("SkillRuntimeError", joined)
            assistant_messages = [item for item in messages if item["role"] == "assistant"]
            self.assertEqual(assistant_messages[-1]["status"], "completed")
            self.assertIn("sandbox unavailable", assistant_messages[-1]["content"])
        finally:
            self._unlink_db(db_path)

    def test_stream_agent_message_blocks_high_risk_tool_preflight(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("stream-risk-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("stream-risk-agent", {"title": "risk"})

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            return {
                                "choices": [
                                    {
                                        "message": {
                                            "content": json.dumps(
                                                {"tool_calls": [{"tool": "shell.run", "arguments": {"command": "rm -rf /"}}]}
                                            )
                                        }
                                    }
                                ],
                                "usage": {},
                            }

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            with mock.patch(
                                "ai_applications.application.services.gateway.stream_chat_completions",
                                side_effect=AssertionError("main stream should not run after high-risk preflight"),
                            ):
                                events = list(
                                    ai_applications.stream_agent_message(
                                        "stream-risk-agent",
                                        conversation["conversation_key"],
                                        {"content": "delete everything", "variables": {}},
                                    )
                                )
                        messages = ai_applications.list_agent_messages("stream-risk-agent", conversation["conversation_key"])["items"]

            joined = "".join(events)
            self.assertIn("event: agent_tool_result", joined)
            self.assertIn("AgentToolRiskError", joined)
            self.assertIn("风险过高", joined)
            assistant_messages = [item for item in messages if item["role"] == "assistant"]
            self.assertEqual(assistant_messages[-1]["status"], "failed")
            self.assertIn("风险过高", assistant_messages[-1]["content"])
            tool_messages = [item for item in messages if item["role"] == "tool"]
            self.assertEqual(tool_messages[-1]["metadata"]["agent_tool_results"][0]["risk"]["level"], "high")
        finally:
            self._unlink_db(db_path)

    def test_stream_agent_message_fails_when_model_asks_for_solo_confirmation(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("stream-confirm-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("stream-confirm-agent", {"title": "confirm"})

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            return {"choices": [{"message": {"content": json.dumps({"tool_calls": []})}}], "usage": {}}

                        def fake_stream_chat_completions(**kwargs: object) -> object:
                            yield 'data: {"choices":[{"delta":{"content":"请确认是否执行这个 shell 命令？"}}]}\n\n'
                            raise AssertionError("stream should stop after solo confirmation boundary")

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            with mock.patch(
                                "ai_applications.application.services.gateway.stream_chat_completions",
                                side_effect=fake_stream_chat_completions,
                            ):
                                events = list(
                                    ai_applications.stream_agent_message(
                                        "stream-confirm-agent",
                                        conversation["conversation_key"],
                                        {"content": "run it", "variables": {}},
                                    )
                                )
                        messages = ai_applications.list_agent_messages("stream-confirm-agent", conversation["conversation_key"])["items"]

            joined = "".join(events)
            self.assertIn("Solo 模式不支持用户确认式工具调用", joined)
            self.assertNotIn("请确认是否执行这个 shell 命令？", joined)
            assistant_messages = [item for item in messages if item["role"] == "assistant"]
            self.assertEqual(assistant_messages[-1]["status"], "failed")
            self.assertIn("Solo 模式不支持用户确认式工具调用", assistant_messages[-1]["content"])
        finally:
            self._unlink_db(db_path)

    def test_stream_agent_message_stops_repeated_native_tool_call_chunks(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("stream-loop-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("stream-loop-agent", {"title": "loop"})

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            return {"choices": [{"message": {"content": json.dumps({"tool_calls": []})}}], "usage": {}}

                        def fake_stream_chat_completions(**kwargs: object) -> object:
                            yield 'data: {"choices":[{"delta":{"content":"步骤1 "}}]}\n\n'
                            yield 'data: {"choices":[{"delta":{"content":"|<tool_call>"}}]}\n\n'
                            yield 'data: {"choices":[{"delta":{"content":"{\\"name\\":\\"bash\\",\\"arguments\\":{\\"cmd\\":\\"ls\\"}}"}}]}\n\n'
                            yield 'data: {"choices":[{"delta":{"content":"|</tool_call>"}}]}\n\n'
                            raise AssertionError("stream should stop before later chunks")

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            with mock.patch(
                                "ai_applications.application.services.gateway.stream_chat_completions",
                                side_effect=fake_stream_chat_completions,
                            ):
                                events = list(
                                    ai_applications.stream_agent_message(
                                        "stream-loop-agent",
                                        conversation["conversation_key"],
                                        {"content": "分析日志", "variables": {}},
                                    )
                                )
                        messages = ai_applications.list_agent_messages("stream-loop-agent", conversation["conversation_key"])["items"]

            joined = "".join(events)
            self.assertIn("步骤1", joined)
            self.assertIn("未被当前流式阶段接管", joined)
            self.assertTrue(joined.rstrip().endswith("data: [DONE]"))
            assistant_messages = [item for item in messages if item["role"] == "assistant"]
            self.assertEqual(assistant_messages[-1]["status"], "failed")
            self.assertIn("未被当前流式阶段接管", assistant_messages[-1]["content"])
        finally:
            self._unlink_db(db_path)

    def test_stream_agent_message_stops_split_tool_result_chunks(self) -> None:
        db_path = self._temporary_db_path()
        workspace_root = Path(".tmp/test-agent-workspaces") / uuid.uuid4().hex
        self._initialize_llm_db(db_path)
        try:
            with mock.patch.dict("os.environ", {"OPS_ADMIN_AGENT_WORKSPACE_ROOT": str(workspace_root)}, clear=False):
                with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                    with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                        payload = self._sample_ai_application("stream-tool-result-agent")
                        payload["app_type"] = "agent"
                        payload["user_prompt_template"] = ""
                        payload["variables_schema"] = {}
                        ai_applications.save_ai_application(payload)
                        conversation = ai_applications.create_agent_conversation("stream-tool-result-agent", {"title": "tool-result"})

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            return {"choices": [{"message": {"content": json.dumps({"tool_calls": []})}}], "usage": {}}

                        def fake_stream_chat_completions(**kwargs: object) -> object:
                            yield 'data: {"choices":[{"delta":{"content":"prefix <tool_"}}]}\n\n'
                            yield 'data: {"choices":[{"delta":{"content":"result>{\\"result\\":\\"ls /tmp\\"}"}}]}\n\n'
                            yield 'data: {"choices":[{"delta":{"content":"</tool_"}}]}\n\n'
                            yield 'data: {"choices":[{"delta":{"content":"result>"}}]}\n\n'
                            yield 'data: {"choices":[{"delta":{"content":"<tool_"}}]}\n\n'
                            yield 'data: {"choices":[{"delta":{"content":"result>{\\"result\\":\\"ls /\\"}"}}]}\n\n'
                            raise AssertionError("stream should stop after split tool_result markers")

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            with mock.patch(
                                "ai_applications.application.services.gateway.stream_chat_completions",
                                side_effect=fake_stream_chat_completions,
                            ):
                                events = list(
                                    ai_applications.stream_agent_message(
                                        "stream-tool-result-agent",
                                        conversation["conversation_key"],
                                        {"content": "read pdf", "variables": {}},
                                    )
                                )
                        messages = ai_applications.list_agent_messages("stream-tool-result-agent", conversation["conversation_key"])["items"]

            joined = "".join(events)
            self.assertNotIn("prefix <tool_", joined)
            self.assertNotIn("<tool_", joined)
            self.assertIn("run_command", joined)
            assistant_messages = [item for item in messages if item["role"] == "assistant"]
            self.assertEqual(assistant_messages[-1]["status"], "failed")
            self.assertIn("未被当前流式阶段接管", assistant_messages[-1]["content"])
        finally:
            self._unlink_db(db_path)

    def test_agent_application_does_not_use_single_turn_run_endpoint(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    payload = self._sample_ai_application("support-agent")
                    payload["app_type"] = "agent"
                    payload["user_prompt_template"] = ""
                    payload["variables_schema"] = {}
                    ai_applications.save_ai_application(payload)
                    with self.assertRaises(Exception) as raised:
                        ai_applications.run_draft_application("support-agent", {"variables": {}})

            self.assertIn("agent conversation", str(getattr(raised.exception, "detail", "")).lower())
        finally:
            self._unlink_db(db_path)

    def test_workflow_ai_application_runs_without_new_storage(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    payload = self._sample_ai_application("meeting-workflow")
                    payload["app_type"] = "workflow"
                    payload["variables_schema"] = {"type": "object", "required": ["content"]}
                    payload["runtime_config"] = {
                        "workflow": {
                            "nodes": [
                                {"id": "start", "type": "start", "data": {}},
                                {
                                    "id": "llm_1",
                                    "type": "llm",
                                    "data": {
                                        "model": "dashscope.qwen-plus",
                                        "system_prompt": "你是会议纪要助手",
                                        "user_prompt_template": "请整理：{{content}}",
                                        "output_key": "summary",
                                    },
                                },
                                {"id": "end", "type": "end", "data": {"output": "{{summary}}"}},
                            ],
                            "edges": [
                                {"source": "start", "target": "llm_1"},
                                {"source": "llm_1", "target": "end"},
                            ],
                        }
                    }
                    ai_applications.save_ai_application(payload)

                    def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                        messages = kwargs["messages"]
                        assert isinstance(messages, list)
                        self.assertEqual(messages[-1]["content"], "请整理：会议内容")
                        return {"choices": [{"message": {"content": "会议纪要"}}], "usage": {"total_tokens": 11}}

                    with mock.patch(
                        "ai_applications.application.services.gateway.chat_completions",
                        side_effect=fake_chat_completions,
                    ):
                        result = ai_applications.run_draft_application(
                            "meeting-workflow",
                            {"variables": {"content": "会议内容"}},
                        )

            self.assertEqual(result["answer"], "会议纪要")
            self.assertEqual(result["usage"]["total_tokens"], 11)
            self.assertEqual(result["trace"]["rendered_messages"][-1]["role"], "workflow_trace")
        finally:
            self._unlink_db(db_path)

    def test_workflow_script_node_transforms_application_variables(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    payload = self._sample_ai_application("script-workflow")
                    payload["app_type"] = "workflow"
                    payload["variables_schema"] = {"type": "object", "required": ["orders"]}
                    payload["runtime_config"] = {
                        "workflow": {
                            "nodes": [
                                {"id": "start", "type": "start", "data": {}},
                                {
                                    "id": "script_1",
                                    "type": "script",
                                    "data": {
                                        "input": "{{orders}}",
                                        "code": "\n".join(
                                            [
                                                "paid = [item for item in input if item.get('status') == 'paid']",
                                                "result = {",
                                                "  'count': len(paid),",
                                                "  'total': sum(item.get('amount', 0) for item in paid),",
                                                "}",
                                            ]
                                        ),
                                        "output_key": "summary",
                                    },
                                },
                                {"id": "end", "type": "end", "data": {"output": "{{summary.total}}"}},
                            ],
                            "edges": [
                                {"source": "start", "target": "script_1"},
                                {"source": "script_1", "target": "end"},
                            ],
                        }
                    }
                    ai_applications.save_ai_application(payload)
                    result = ai_applications.run_draft_application(
                        "script-workflow",
                        {
                            "variables": {
                                "orders": [
                                    {"status": "paid", "amount": 12},
                                    {"status": "draft", "amount": 40},
                                    {"status": "paid", "amount": 8},
                                ]
                            }
                        },
                    )

            self.assertEqual(result["answer"], "20")
            workflow_trace = result["trace"]["rendered_messages"][-1]["content"]["workflow"]
            self.assertEqual([item["node_id"] for item in workflow_trace["nodes"]], ["start", "script_1", "end"])
            self.assertEqual(workflow_trace["nodes"][1]["node_type"], "script")
            self.assertEqual(workflow_trace["nodes"][1]["output"]["result"]["count"], 2)
        finally:
            self._unlink_db(db_path)

    def test_workflow_file_extract_node_passes_content_to_next_node(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    payload = self._sample_ai_application("file-extract-workflow")
                    payload["app_type"] = "workflow"
                    payload["variables_schema"] = {"type": "object", "required": ["document"]}
                    payload["runtime_config"] = {
                        "workflow": {
                            "nodes": [
                                {"id": "start", "type": "start", "data": {}},
                                {
                                    "id": "file_extract_1",
                                    "type": "file_extract",
                                    "data": {
                                        "input": "{{document}}",
                                        "output_key": "file_content",
                                        "max_chars": 1000,
                                    },
                                },
                                {
                                    "id": "script_1",
                                    "type": "script",
                                    "data": {
                                        "input": "{{file_content}}",
                                        "code": "result = {'summary': input.get('text', '').replace('原文：', '')}",
                                        "output_key": "processed",
                                    },
                                },
                                {"id": "end", "type": "end", "data": {"output": "{{processed.summary}}" }},
                            ],
                            "edges": [
                                {"source": "start", "target": "file_extract_1"},
                                {"source": "file_extract_1", "target": "script_1"},
                                {"source": "script_1", "target": "end"},
                            ],
                        }
                    }
                    ai_applications.save_ai_application(payload)
                    result = ai_applications.run_draft_application(
                        "file-extract-workflow",
                        {
                            "variables": {
                                "document": {
                                    "type": "file",
                                    "name": "meeting.txt",
                                    "mime_type": "text/plain",
                                    "size": 24,
                                    "text": "原文：会议纪要内容",
                                }
                            }
                        },
                    )

            self.assertEqual(result["answer"], "会议纪要内容")
            workflow_trace = result["trace"]["rendered_messages"][-1]["content"]["workflow"]
            self.assertEqual([item["node_id"] for item in workflow_trace["nodes"]], ["start", "file_extract_1", "script_1", "end"])
            self.assertEqual(workflow_trace["nodes"][1]["node_type"], "file_extract")
            self.assertEqual(workflow_trace["nodes"][1]["output"]["file_count"], 1)
            self.assertEqual(workflow_trace["nodes"][1]["output"]["text"], "原文：会议纪要内容")
        finally:
            self._unlink_db(db_path)

    def test_workflow_node_system_prompt_is_not_truncated_when_saved(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    long_system_prompt = "系统提示词" * 2400
                    payload = self._sample_ai_application("long-workflow-prompt")
                    payload["app_type"] = "workflow"
                    payload["runtime_config"] = {
                        "workflow": {
                            "nodes": [
                                {"id": "start", "type": "start", "data": {}},
                                {
                                    "id": "llm_1",
                                    "type": "llm",
                                    "data": {
                                        "model": "dashscope.qwen-plus",
                                        "system_prompt": long_system_prompt,
                                        "user_prompt_template": "请处理：{{content}}",
                                        "output_key": "summary",
                                    },
                                },
                                {"id": "end", "type": "end", "data": {"output": "{{summary}}" }},
                            ],
                            "edges": [
                                {"source": "start", "target": "llm_1"},
                                {"source": "llm_1", "target": "end"},
                            ],
                        }
                    }

                    saved = ai_applications.save_ai_application(payload)

            saved_prompt = saved["runtime_config"]["workflow"]["nodes"][1]["data"]["system_prompt"]
            self.assertEqual(saved_prompt, long_system_prompt)
            self.assertNotIn("[truncated", saved_prompt)
        finally:
            self._unlink_db(db_path)

    def test_workflow_ignores_downstream_schema_required_variables(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    payload = self._sample_ai_application("branch-workflow")
                    payload["app_type"] = "workflow"
                    payload["variables_schema"] = {"type": "object", "required": ["content"]}
                    payload["runtime_config"] = {
                        "workflow": {
                            "nodes": [
                                {
                                    "id": "start",
                                    "type": "start",
                                    "data": {
                                        "variables": [
                                            {"key": "input", "label": "输入", "type": "text", "required": True}
                                        ]
                                    },
                                },
                                {"id": "condition_1", "type": "condition", "data": {"left": "{{input}}", "operator": "exists"}},
                                {"id": "end", "type": "end", "data": {"output": "{{input}}"}},
                            ],
                            "edges": [
                                {"source": "start", "target": "condition_1"},
                                {"source": "condition_1", "target": "end", "sourceHandle": "true"},
                            ],
                        }
                    }
                    ai_applications.save_ai_application(payload)
                    result = ai_applications.run_draft_application("branch-workflow", {"variables": {"input": "hello"}})

            self.assertEqual(result["answer"], "hello")
            workflow_trace = result["trace"]["rendered_messages"][-1]["content"]["workflow"]
            self.assertEqual([item["node_id"] for item in workflow_trace["nodes"]], ["start", "condition_1", "end"])
            self.assertEqual(workflow_trace["nodes"][1]["branch"], "true")
        finally:
            self._unlink_db(db_path)

    def test_ai_capability_owns_prompt_runtime_and_executes(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    with mock.patch("ai_capabilities.application.services.require_database", return_value=db_path):
                        capability = ai_capabilities.save_ai_capability(
                            {
                                "capability_key": "summarize",
                                "name": "摘要生成",
                                "description": "平台内部摘要生成能力",
                                "scope": "tenant",
                                "system_prompt": "你是摘要助手",
                                "user_prompt_template": "请总结：{{question}}",
                                "input_schema": {"type": "object", "required": ["question"]},
                                "model_preferences": {"model": "dashscope.qwen-plus", "temperature": 0.2},
                                "enabled": True,
                            }
                        )

                        def fake_chat_completions(**kwargs: object) -> dict[str, object]:
                            messages = kwargs["messages"]
                            assert isinstance(messages, list)
                            self.assertEqual(messages[0]["content"], "你是摘要助手")
                            self.assertEqual(messages[-1]["content"], "请总结：会议内容")
                            return {"choices": [{"message": {"content": "会议摘要"}}], "usage": {"total_tokens": 9}}

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            side_effect=fake_chat_completions,
                        ):
                            result = ai_capabilities.execute_ai_capability(
                                "summarize",
                                {"variables": {"question": "会议内容"}},
                            )

                        capabilities = ai_capabilities.list_ai_capabilities()["items"]
                        traces = ai_applications.list_prompt_runtime_traces()["items"]

            self.assertEqual(capability["binding_type"], "prompt_runtime")
            self.assertEqual(capability["binding_key"], "summarize")
            self.assertEqual(capability["model_preferences"]["model"], "dashscope.qwen-plus")
            self.assertEqual(capabilities[0]["user_prompt_template"], "请总结：{{question}}")
            self.assertEqual(capabilities[0]["call_method"], "aiService.execute")
            self.assertEqual(result["answer"], "会议摘要")
            self.assertEqual(result["trace"]["caller_type"], "ai_capability")
            self.assertEqual(result["trace"]["caller_key"], "summarize")
            self.assertEqual(traces[0]["caller_type"], "ai_capability")
            self.assertEqual(traces[0]["caller_key"], "summarize")
        finally:
            self._unlink_db(db_path)

    def test_tenant_can_use_platform_ai_capability_with_tenant_override(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    with mock.patch("ai_capabilities.application.services.require_database", return_value=db_path):
                        platform = set_tenant_scope(
                            TenantScope(
                                tenant_id=1,
                                tenant_key="platform",
                                tenant_name="Platform Administration",
                                is_platform_admin=True,
                            )
                        )
                        try:
                            platform_capability = ai_capabilities.save_platform_ai_capability(
                                {
                                    "capability_key": "summarize",
                                    "name": "平台摘要",
                                    "description": "平台统一摘要能力",
                                    "system_prompt": "你是平台摘要助手",
                                    "user_prompt_template": "平台总结：{{question}}",
                                    "input_schema": {"type": "object", "required": ["question"]},
                                    "model_preferences": {"model": "dashscope.qwen-plus", "temperature": 0.2},
                                    "enabled": True,
                                }
                            )
                        finally:
                            reset_tenant_scope(platform)

                        tenant = set_tenant_scope(TenantScope(tenant_id=22, tenant_key="tenant-a", tenant_name="Tenant A"))
                        try:
                            inherited = ai_capabilities.get_ai_capability("summarize")
                            inherited_items = ai_capabilities.list_ai_capabilities()["items"]

                            def fake_platform_chat(**kwargs: object) -> dict[str, object]:
                                messages = kwargs["messages"]
                                assert isinstance(messages, list)
                                self.assertEqual(messages[0]["content"], "你是平台摘要助手")
                                self.assertEqual(messages[-1]["content"], "平台总结：会议内容")
                                return {"choices": [{"message": {"content": "平台摘要结果"}}], "usage": {"total_tokens": 9}}

                            with mock.patch(
                                "ai_applications.application.services.gateway.chat_completions",
                                side_effect=fake_platform_chat,
                            ):
                                platform_result = ai_capabilities.execute_ai_capability(
                                    "summarize",
                                    {"variables": {"question": "会议内容"}},
                                )

                            tenant_capability = ai_capabilities.save_ai_capability(
                                {
                                    "capability_key": "summarize",
                                    "name": "租户摘要",
                                    "description": "租户覆盖摘要能力",
                                    "system_prompt": "你是租户摘要助手",
                                    "user_prompt_template": "租户总结：{{question}}",
                                    "input_schema": {"type": "object", "required": ["question"]},
                                    "model_preferences": {"model": "dashscope.qwen-plus", "temperature": 0.2},
                                    "enabled": True,
                                }
                            )

                            def fake_tenant_chat(**kwargs: object) -> dict[str, object]:
                                messages = kwargs["messages"]
                                assert isinstance(messages, list)
                                self.assertEqual(messages[0]["content"], "你是租户摘要助手")
                                self.assertEqual(messages[-1]["content"], "租户总结：会议内容")
                                return {"choices": [{"message": {"content": "租户摘要结果"}}], "usage": {"total_tokens": 7}}

                            with mock.patch(
                                "ai_applications.application.services.gateway.chat_completions",
                                side_effect=fake_tenant_chat,
                            ):
                                tenant_result = ai_capabilities.execute_ai_capability(
                                    "summarize",
                                    {"variables": {"question": "会议内容"}},
                                )
                            overridden_items = ai_capabilities.list_ai_capabilities()["items"]
                        finally:
                            reset_tenant_scope(tenant)

            self.assertEqual(platform_capability["tenant_id"], 1)
            self.assertEqual(platform_capability["scope"], "platform")
            self.assertEqual(inherited["scope"], "platform")
            self.assertEqual(inherited_items[0]["name"], "平台摘要")
            self.assertEqual(platform_result["answer"], "平台摘要结果")
            self.assertEqual(tenant_capability["tenant_id"], 22)
            self.assertEqual(tenant_capability["scope"], "tenant")
            self.assertEqual(tenant_result["answer"], "租户摘要结果")
            self.assertIn("prompt.polish", [item["capability_key"] for item in overridden_items])
            self.assertEqual([item["capability_key"] for item in overridden_items if item["capability_key"] == "summarize"], ["summarize"])
            self.assertEqual(overridden_items[0]["name"], "租户摘要")
        finally:
            self._unlink_db(db_path)

    def test_ai_capability_requires_prompt_runtime_config_before_execute(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_capabilities.application.services.require_database", return_value=db_path):
                    ai_capabilities.save_ai_capability(
                        {
                            "capability_key": "summarize",
                            "name": "摘要生成",
                            "user_prompt_template": "",
                            "model_preferences": {},
                        }
                    )
                    with self.assertRaises(Exception) as raised:
                        ai_capabilities.execute_ai_capability("summarize", {"variables": {"question": "会议内容"}})

            self.assertIn("user_prompt_template is required before execute", str(getattr(raised.exception, "detail", "")))
        finally:
            self._unlink_db(db_path)

    def test_ai_capability_can_execute_workflow_runtime(self) -> None:
        db_path = self._temporary_db_path()
        self._initialize_llm_db(db_path)
        try:
            with mock.patch("llm_runtime.application.services.resolve_db_path", return_value=db_path):
                with mock.patch("ai_applications.application.services.require_database", return_value=db_path):
                    with mock.patch("ai_capabilities.application.services.require_database", return_value=db_path):
                        ai_capabilities.save_ai_capability(
                            {
                                "capability_key": "meeting-summary",
                                "name": "会议纪要",
                                "binding_type": "workflow_runtime",
                                "input_schema": {"type": "object", "required": ["content"]},
                                "runtime_config": {
                                    "workflow": {
                                        "nodes": [
                                            {"id": "start", "type": "start", "data": {}},
                                            {
                                                "id": "llm_1",
                                                "type": "llm",
                                                "data": {
                                                    "model": "dashscope.qwen-plus",
                                                    "system_prompt": "你是会议纪要助手",
                                                    "user_prompt_template": "请整理：{{content}}",
                                                },
                                            },
                                            {"id": "end", "type": "end", "data": {}},
                                        ],
                                        "edges": [
                                            {"source": "start", "target": "llm_1"},
                                            {"source": "llm_1", "target": "end"},
                                        ],
                                    }
                                },
                            }
                        )

                        with mock.patch(
                            "ai_applications.application.services.gateway.chat_completions",
                            return_value={"choices": [{"message": {"content": "能力会议纪要"}}], "usage": {}},
                        ):
                            result = ai_capabilities.execute_ai_capability(
                                "meeting-summary",
                                {"variables": {"content": "会议内容"}},
                            )

            self.assertEqual(result["answer"], "能力会议纪要")
            self.assertEqual(result["trace"]["caller_type"], "ai_capability")
        finally:
            self._unlink_db(db_path)

    @staticmethod
    def _temporary_db_path() -> Path:
        temp_root = Path(".tmp/test-dbs")
        temp_root.mkdir(parents=True, exist_ok=True)
        return temp_root / f"llm-runtime-{uuid.uuid4().hex}.db"

    @staticmethod
    def _unlink_db(db_path: Path) -> None:
        for path in [db_path, db_path.with_name(db_path.name + "-wal"), db_path.with_name(db_path.name + "-shm")]:
            path.unlink(missing_ok=True)

    @staticmethod
    def _initialize_llm_db(db_path: Path) -> None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_llm_schema(conn)
            ensure_ai_applications_schema(conn)
            ensure_ai_capabilities_schema(conn)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _initialize_ai_assets_db(db_path: Path) -> None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_ai_assets_schema(conn)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _image_data_url(width: int = 64, height: int = 64, color: tuple[int, int, int] = (30, 120, 220)) -> str:
        image = Image.new("RGB", (width, height), color)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        payload = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{payload}"

    @staticmethod
    def _sample_ai_application(app_key: str) -> dict[str, object]:
        return {
            "app_key": app_key,
            "name": app_key.title(),
            "description": "",
            "app_type": "single_turn_generation",
            "status": "draft",
            "system_prompt": "你是一个简洁的助手",
            "developer_prompt": "",
            "user_prompt_template": "请总结：{{question}}",
            "variables_schema": {"type": "object", "required": ["question"]},
            "model_preferences": {"model": "dashscope.qwen-plus", "temperature": 0.2},
            "trace_policy": {"enabled": True},
        }

    @staticmethod
    def _seed_route(db_path: Path) -> None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_llm_schema(conn)
            repositories.upsert_provider(
                conn,
                {
                    "provider_key": "dashscope",
                    "display_name": "閫氫箟鐧剧偧",
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "api_key": "sk-dashscope",
                    "enabled": True,
                },
            )
            repositories.upsert_provider(
                conn,
                {
                    "provider_key": "siliconflow",
                    "display_name": "纭呭熀娴佸姩",
                    "base_url": "https://api.siliconflow.cn/v1",
                    "api_key": "sk-siliconflow",
                    "enabled": True,
                },
            )
            repositories.upsert_model(
                conn,
                {
                    "model_key": "dashscope.qwen-plus",
                    "provider_key": "dashscope",
                    "model_name": "qwen-plus",
                    "enabled": True,
                },
            )
            repositories.upsert_model(
                conn,
                {
                    "model_key": "siliconflow.qwen3-32b",
                    "provider_key": "siliconflow",
                    "model_name": "Qwen/Qwen3-32B",
                    "enabled": True,
                },
            )
            repositories.register_task(
                conn,
                {
                    "task_key": "ops.sample.rank",
                    "display_name": "鍔熻兘鐐规帹鑽?鎺掑簭",
                    "owner_context": "ops",
                },
            )
            repositories.upsert_routing_policy(
                conn,
                {
                    "route_key": "ops.sample.rank",
                    "strategy": "priority",
                    "entries": [
                        {
                            "model_key": "dashscope.qwen-plus",
                            "priority": 1,
                            "response_format": "json",
                        },
                        {
                            "model_key": "siliconflow.qwen3-32b",
                            "priority": 2,
                            "response_format": "json",
                        },
                    ],
                },
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _seed_single_route(db_path: Path, *, provider_key: str, model_key: str) -> None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_llm_schema(conn)
            repositories.upsert_provider(
                conn,
                {
                    "provider_key": provider_key,
                    "display_name": provider_key,
                    "base_url": f"https://{provider_key}.example/v1",
                    "api_key": f"sk-{provider_key}",
                    "enabled": True,
                },
            )
            repositories.upsert_model(
                conn,
                {
                    "model_key": model_key,
                    "provider_key": provider_key,
                    "model_name": model_key,
                    "enabled": True,
                },
            )
            repositories.register_task(
                conn,
                {
                    "task_key": "ops.sample.rank",
                    "display_name": "rank",
                    "owner_context": "ops",
                },
            )
            repositories.upsert_routing_policy(
                conn,
                {
                    "route_key": "ops.sample.rank",
                    "strategy": "priority",
                    "entries": [{"model_key": model_key, "priority": 1, "response_format": "json"}],
                },
            )
            conn.commit()
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()



