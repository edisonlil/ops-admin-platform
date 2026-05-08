from __future__ import annotations

import sqlite3
import unittest
import uuid
from pathlib import Path
from unittest import mock
import json

from framework.llm_core import LLMResponse, OpenAICompatibleLLMClient
from llm_runtime.application import gateway
from llm_runtime.application import services
from llm_runtime.infrastructure.persistence.bootstrap import ensure_llm_schema
from llm_runtime.infrastructure.persistence import repositories
from system.application.tenancy import reset_tenant_scope, set_tenant_scope
from system.domain.tenancy import TenantScope


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
            conn.commit()
        finally:
            conn.close()

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


