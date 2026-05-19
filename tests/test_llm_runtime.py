from __future__ import annotations

import sqlite3
import unittest
import uuid
from pathlib import Path
from unittest import mock
import json

from framework.llm_core import LLMResponse, OpenAICompatibleLLMClient
from ai_capabilities.application import services as ai_capabilities
from ai_applications.application import services as ai_applications
from ai_applications.infrastructure.persistence.bootstrap import ensure_ai_applications_schema
from ai_capabilities.infrastructure.persistence.bootstrap import ensure_ai_capabilities_schema
from llm_runtime.application import gateway
from llm_runtime.application import services
from llm_runtime.infrastructure.persistence.bootstrap import ensure_llm_schema
from llm_runtime.infrastructure.persistence import repositories
from system.application.tenancy import reset_tenant_scope, set_tenant_scope
from system.application.data_access import DataAccessPredicate, SCOPE_SELF
from system.domain.tenancy import TenantScope
from ai_assets.infrastructure.persistence.bootstrap import ensure_ai_assets_schema
from ai_assets.application import services as ai_asset_services


class LLMRuntimeTests(unittest.TestCase):
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
                items = repositories.list_call_logs(
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
        self.assertEqual(content[0]["type"], "audio_url")
        self.assertEqual(content[0]["audio_url"]["url"], "data:audio/mpeg;base64,abc")
        self.assertEqual(content[1]["type"], "text")

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
                        self.assertEqual(content[1]["image_url"]["url"], "data:image/png;base64,abc")
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
                                        "data_url": "data:image/png;base64,abc",
                                    }
                                }
                            },
                        )

            self.assertEqual(result["answer"], "图片里有一个按钮")
            self.assertIn("[image]", result["trace"]["rendered_prompt"])
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


