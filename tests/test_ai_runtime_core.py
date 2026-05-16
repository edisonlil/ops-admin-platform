from __future__ import annotations

import unittest

from ai_runtime_core.workflow_runtime import WorkflowLLMRequest
from ai_runtime_core.workflow_runtime import WorkflowLLMResult
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


if __name__ == "__main__":
    unittest.main()
