from __future__ import annotations

import unittest

from ai_runtime_core.workflow_runtime import WorkflowLLMRequest
from ai_runtime_core.workflow_runtime import WorkflowLLMResult
from ai_runtime_core.workflow_runtime import WorkflowRuntimeError
from ai_runtime_core.workflow_runtime import WorkflowSQLRequest
from ai_runtime_core.workflow_runtime import WorkflowSQLResult
from ai_runtime_core.workflow_runtime import execute_workflow


class AIRuntimeCoreTests(unittest.TestCase):
    def test_workflow_runs_llm_node_and_end_node(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "llm_1",
                    "type": "llm",
                    "data": {
                        "model": "dashscope.qwen-plus",
                        "system_prompt": "你是摘要助手",
                        "user_prompt_template": "请总结：{{content}}",
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
        requests: list[WorkflowLLMRequest] = []

        def fake_llm(request: WorkflowLLMRequest) -> WorkflowLLMResult:
            requests.append(request)
            return WorkflowLLMResult(answer="会议摘要", usage={"total_tokens": 7}, model=request.model)

        result = execute_workflow(definition, {"content": "会议内容"}, llm_executor=fake_llm)

        self.assertEqual(result.answer, "会议摘要")
        self.assertEqual(result.context["variables"]["summary"], "会议摘要")
        self.assertEqual(result.usage["total_tokens"], 7)
        self.assertEqual(requests[0].messages[-1]["content"], "请总结：会议内容")
        self.assertEqual([item["node_id"] for item in result.trace["workflow"]["nodes"]], ["start", "llm_1", "end"])
        self.assertNotIn("summary", result.trace["workflow"]["nodes"][0]["output"]["variables"])

    def test_workflow_condition_routes_false_branch(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "if_1",
                    "type": "condition",
                    "data": {"left": "{{score}}", "operator": "gte", "right": 90},
                },
                {"id": "pass", "type": "end", "data": {"output": "通过"}},
                {"id": "reject", "type": "end", "data": {"output": "退回"}},
            ],
            "edges": [
                {"source": "start", "target": "if_1"},
                {"source": "if_1", "target": "pass", "sourceHandle": "true"},
                {"source": "if_1", "target": "reject", "sourceHandle": "false"},
            ],
        }

        result = execute_workflow(definition, {"score": 60}, llm_executor=lambda request: WorkflowLLMResult(answer=""))

        self.assertEqual(result.answer, "退回")
        condition_trace = result.trace["workflow"]["nodes"][1]
        self.assertEqual(condition_trace["branch"], "false")

    def test_workflow_sql_node_writes_custom_output_variable(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "sql_1",
                    "type": "sql_query",
                    "data": {
                        "sql": "SELECT name, amount FROM orders WHERE status = ?",
                        "params": ["{{status}}"],
                        "output_key": "records",
                        "result_shape": "rows",
                    },
                },
                {
                    "id": "llm_1",
                    "type": "llm",
                    "data": {
                        "model": "dashscope.qwen-plus",
                        "user_prompt_template": "订单：{{records.rows}}",
                        "output_key": "answer",
                    },
                },
                {"id": "end", "type": "end", "data": {"output": "{{answer}}"}} ,
            ],
            "edges": [
                {"source": "start", "target": "sql_1"},
                {"source": "sql_1", "target": "llm_1"},
                {"source": "llm_1", "target": "end"},
            ],
        }
        sql_requests: list[WorkflowSQLRequest] = []
        llm_requests: list[WorkflowLLMRequest] = []

        def fake_sql(request: WorkflowSQLRequest) -> WorkflowSQLResult:
            sql_requests.append(request)
            return WorkflowSQLResult(
                rows=[{"name": "A", "amount": 12}, {"name": "B", "amount": 34}],
                columns=["name", "amount"],
                row_count=2,
            )

        def fake_llm(request: WorkflowLLMRequest) -> WorkflowLLMResult:
            llm_requests.append(request)
            return WorkflowLLMResult(answer="ok", model=request.model)

        result = execute_workflow(
            definition,
            {"status": "paid"},
            llm_executor=fake_llm,
            sql_executor=fake_sql,
        )

        self.assertEqual(result.answer, "ok")
        self.assertEqual(sql_requests[0].params, ["paid"])
        self.assertEqual(result.context["variables"]["records"]["row_count"], 2)
        self.assertEqual(result.context["variables"]["records"]["rows"][0]["name"], "A")
        self.assertIn("records.rows", definition["nodes"][2]["data"]["user_prompt_template"])
        self.assertIn("A", str(llm_requests[0].messages[-1]["content"]))

    def test_workflow_llm_json_response_decodes_fenced_json_and_expands_sql_array_params(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "llm_1",
                    "type": "llm",
                    "data": {
                        "model": "dashscope.qwen-plus",
                        "user_prompt_template": "请输出 JSON",
                        "response_format": {"type": "json_object"},
                        "output_key": "output",
                    },
                },
                {
                    "id": "sql_1",
                    "type": "sql_query",
                    "data": {
                        "sql": "SELECT id FROM docs WHERE primary_component IN (:selected_components)",
                        "params": {"selected_components": "{{output.selected_components}}"},
                        "output_key": "records",
                    },
                },
                {"id": "end", "type": "end", "data": {"output": "{{records.row_count}}"}},
            ],
            "edges": [
                {"source": "start", "target": "llm_1"},
                {"source": "llm_1", "target": "sql_1"},
                {"source": "sql_1", "target": "end"},
            ],
        }
        sql_requests: list[WorkflowSQLRequest] = []

        def fake_llm(request: WorkflowLLMRequest) -> WorkflowLLMResult:
            return WorkflowLLMResult(
                answer='```json\n{"selected_components": ["PUB", "知识库"]}\n```',
                model=request.model,
            )

        def fake_sql(request: WorkflowSQLRequest) -> WorkflowSQLResult:
            sql_requests.append(request)
            return WorkflowSQLResult(rows=[], columns=["id"], row_count=0)

        result = execute_workflow(
            definition,
            {},
            llm_executor=fake_llm,
            sql_executor=fake_sql,
        )

        self.assertEqual(result.context["variables"]["output"]["selected_components"], ["PUB", "知识库"])
        self.assertEqual(sql_requests[0].sql, "SELECT id FROM docs WHERE primary_component IN (?, ?)")
        self.assertEqual(sql_requests[0].params, ["PUB", "知识库"])

    def test_workflow_llm_json_response_prefers_fenced_json_over_inline_example_object(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "llm_1",
                    "type": "llm",
                    "data": {
                        "model": "dashscope.qwen-plus",
                        "user_prompt_template": "请输出 JSON",
                        "response_format": {"type": "json_object"},
                        "output_key": "output",
                    },
                },
                {"id": "end", "type": "end", "data": {"output": "{{output.selected_components}}"}},
            ],
            "edges": [
                {"source": "start", "target": "llm_1"},
                {"source": "llm_1", "target": "end"},
            ],
        }

        result = execute_workflow(
            definition,
            {},
            llm_executor=lambda request: WorkflowLLMResult(
                answer='示例：{"example": true}\n```json\n{"selected_components": ["PUB", "知识库"]}\n```',
                model=request.model,
            ),
        )

        self.assertEqual(result.context["variables"]["output"]["selected_components"], ["PUB", "知识库"])

    def test_workflow_sql_node_rejects_write_statement(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "sql_1",
                    "type": "sql_query",
                    "data": {"sql": "DELETE FROM orders", "output_key": "records"},
                },
            ],
            "edges": [{"source": "start", "target": "sql_1"}],
        }

        with self.assertRaises(WorkflowRuntimeError):
            execute_workflow(
                definition,
                {},
                llm_executor=lambda request: WorkflowLLMResult(answer=""),
                sql_executor=lambda request: WorkflowSQLResult(),
            )

    def test_workflow_sql_node_expands_named_array_params(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "sql_1",
                    "type": "sql_query",
                    "data": {
                        "sql": "SELECT id FROM docs WHERE product_line = :product_line AND primary_component IN (:selected_components)",
                        "params": {
                            "product_line": "文档中台",
                            "selected_components": "{{output.answer.selected_components}}",
                        },
                        "output_key": "records",
                    },
                },
            ],
            "edges": [{"source": "start", "target": "sql_1"}],
        }
        requests: list[WorkflowSQLRequest] = []

        def fake_sql(request: WorkflowSQLRequest) -> WorkflowSQLResult:
            requests.append(request)
            return WorkflowSQLResult(rows=[], columns=["id"], row_count=0)

        execute_workflow(
            definition,
            {"output": {"answer": {"selected_components": ["知识库", "权限"]}}},
            llm_executor=lambda request: WorkflowLLMResult(answer=""),
            sql_executor=fake_sql,
        )

        self.assertEqual(
            requests[0].sql,
            "SELECT id FROM docs WHERE product_line = ? AND primary_component IN (?, ?)",
        )
        self.assertEqual(requests[0].params, ["文档中台", "知识库", "权限"])

    def test_workflow_sql_node_requires_executor(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "sql_1",
                    "type": "sql_query",
                    "data": {"sql": "SELECT 1 AS value", "output_key": "records"},
                },
            ],
            "edges": [{"source": "start", "target": "sql_1"}],
        }

        with self.assertRaises(WorkflowRuntimeError):
            execute_workflow(definition, {}, llm_executor=lambda request: WorkflowLLMResult(answer=""))


if __name__ == "__main__":
    unittest.main()
