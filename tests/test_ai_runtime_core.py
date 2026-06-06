from __future__ import annotations

import base64
from io import BytesIO
import unittest
import zipfile

from ai_runtime_core.workflow_runtime import WorkflowFileExtractRequest
from ai_runtime_core.workflow_runtime import WorkflowFileExtractResult
from ai_runtime_core.workflow_runtime import WorkflowLLMRequest
from ai_runtime_core.workflow_runtime import WorkflowLLMResult
from ai_runtime_core.workflow_runtime import WorkflowRuntimeError
from ai_runtime_core.workflow_runtime import WorkflowSQLRequest
from ai_runtime_core.workflow_runtime import WorkflowSQLResult
from ai_runtime_core.workflow_runtime import execute_workflow
from ai_runtime_core.workflow_runtime import iter_workflow_events


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

    def test_workflow_events_emit_node_progress_before_completion(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "llm_1",
                    "type": "llm",
                    "data": {
                        "model": "dashscope.qwen-plus",
                        "user_prompt_template": "{{content}}",
                    },
                },
                {"id": "end", "type": "end", "data": {}},
            ],
            "edges": [
                {"source": "start", "target": "llm_1"},
                {"source": "llm_1", "target": "end"},
            ],
        }

        events = list(
            iter_workflow_events(
                definition,
                {"content": "hello"},
                llm_executor=lambda request: WorkflowLLMResult(answer="ok", model=request.model),
            )
        )

        self.assertEqual(events[0]["event"], "workflow.node.started")
        self.assertEqual(events[0]["node"]["node_id"], "start")
        self.assertIn("workflow.node.completed", [item["event"] for item in events[:-1]])
        self.assertEqual(events[-1]["event"], "workflow.completed")
        self.assertEqual(events[-1]["result"].answer, "ok")

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

    def test_workflow_script_node_transforms_data_and_writes_output_variable(self) -> None:
        definition = {
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
                                "  'names': [item.get('name') for item in paid],",
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

        result = execute_workflow(
            definition,
            {
                "orders": [
                    {"name": "A", "status": "paid", "amount": 12},
                    {"name": "B", "status": "draft", "amount": 40},
                    {"name": "C", "status": "paid", "amount": 8},
                ]
            },
            llm_executor=lambda request: WorkflowLLMResult(answer=""),
        )

        self.assertEqual(result.answer, "20")
        self.assertEqual(result.context["variables"]["summary"]["count"], 2)
        self.assertEqual(result.context["variables"]["summary"]["names"], ["A", "C"])
        script_trace = result.trace["workflow"]["nodes"][1]
        self.assertEqual(script_trace["node_type"], "script")
        self.assertEqual(script_trace["output"]["result"]["total"], 20)

    def test_workflow_skill_node_is_not_supported(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "skill_1",
                    "type": "skill",
                    "data": {
                        "skill_key": "log-analysis",
                        "input": {"query": "{{query}}"},
                        "output_key": "skill_result",
                    },
                },
                {"id": "end", "type": "end", "data": {"output": "{{skill_result.summary}}" }},
            ],
            "edges": [
                {"source": "start", "target": "skill_1"},
                {"source": "skill_1", "target": "end"},
            ],
        }
        with self.assertRaisesRegex(WorkflowRuntimeError, "does not support Skill nodes"):
            execute_workflow(
                definition,
                {"query": "error"},
                llm_executor=lambda request: WorkflowLLMResult(answer=""),
            )

    def test_workflow_script_node_can_parse_json_from_previous_node(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "script_1",
                    "type": "script",
                    "data": {
                        "input": "{{payload}}",
                        "code": "data = json.loads(input)\nresult = {'items': data.get('items', []), 'size': len(data.get('items', []))}",
                        "output_key": "parsed",
                    },
                },
                {"id": "end", "type": "end", "data": {"output": "{{parsed.size}}"}},
            ],
            "edges": [
                {"source": "start", "target": "script_1"},
                {"source": "script_1", "target": "end"},
            ],
        }

        result = execute_workflow(
            definition,
            {"payload": '{"items": [1, 2, 3]}'},
            llm_executor=lambda request: WorkflowLLMResult(answer=""),
        )

        self.assertEqual(result.answer, "3")
        self.assertEqual(result.context["variables"]["parsed"]["items"], [1, 2, 3])

    def test_workflow_script_node_rejects_unsafe_code(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "script_1",
                    "type": "script",
                    "data": {
                        "code": "import os\nresult = os.listdir('.')",
                        "output_key": "files",
                    },
                },
            ],
            "edges": [{"source": "start", "target": "script_1"}],
        }

        with self.assertRaises(WorkflowRuntimeError):
            execute_workflow(definition, {}, llm_executor=lambda request: WorkflowLLMResult(answer=""))

    def test_workflow_file_extract_node_writes_text_output_variable(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "file_extract_1",
                    "type": "file_extract",
                    "data": {"input": "{{document}}", "output_key": "file_content", "max_chars": 20},
                },
                {"id": "end", "type": "end", "data": {"output": "{{file_content.text}}" }},
            ],
            "edges": [
                {"source": "start", "target": "file_extract_1"},
                {"source": "file_extract_1", "target": "end"},
            ],
        }

        result = execute_workflow(
            definition,
            {
                "document": {
                    "type": "file",
                    "name": "meeting.txt",
                    "mime_type": "text/plain",
                    "size": 12,
                    "text": "会议纪要内容",
                }
            },
            llm_executor=lambda request: WorkflowLLMResult(answer=""),
        )

        self.assertEqual(result.answer, "会议纪要内容")
        self.assertEqual(result.context["variables"]["file_content"]["file_count"], 1)
        self.assertEqual(result.context["variables"]["file_content"]["files"][0]["name"], "meeting.txt")
        self.assertFalse(result.context["variables"]["file_content"]["truncated"])

    def test_workflow_file_extract_node_decodes_text_data_url_and_truncates(self) -> None:
        content = base64.b64encode("第一行\n第二行\n第三行".encode("utf-8")).decode("ascii")
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "file_extract_1",
                    "type": "file_extract",
                    "data": {"input": "{{documents}}", "output_key": "extracted", "max_chars": 8},
                },
                {"id": "end", "type": "end", "data": {"output": "{{extracted.truncated}}" }},
            ],
            "edges": [
                {"source": "start", "target": "file_extract_1"},
                {"source": "file_extract_1", "target": "end"},
            ],
        }

        result = execute_workflow(
            definition,
            {
                "documents": [
                    {
                        "type": "file",
                        "name": "notes.txt",
                        "mime_type": "text/plain",
                        "data_url": f"data:text/plain;base64,{content}",
                    },
                    {"type": "file", "name": "extra.md", "mime_type": "text/markdown", "text": "后续内容"},
                ]
            },
            llm_executor=lambda request: WorkflowLLMResult(answer=""),
        )

        self.assertEqual(result.answer, "True")
        self.assertEqual(result.context["variables"]["extracted"]["text"], "第一行\n第二行\n")
        self.assertEqual(result.context["variables"]["extracted"]["file_count"], 2)
        self.assertTrue(result.context["variables"]["extracted"]["files"][1]["truncated"])

    def test_workflow_file_extract_node_decodes_gb18030_text_data_url(self) -> None:
        raw_content = "北京客户清单,WPS365-文档平台\n张三,合同审批"
        encoded_content = base64.b64encode(raw_content.encode("gb18030")).decode("ascii")
        definition = file_extract_definition()

        result = execute_workflow(
            definition,
            {
                "document": {
                    "type": "file",
                    "name": "客户清单.csv",
                    "mime_type": "text/csv",
                    "data_url": f"data:text/csv;base64,{encoded_content}",
                }
            },
            llm_executor=lambda request: WorkflowLLMResult(answer=""),
        )

        self.assertEqual(result.context["variables"]["file_content"]["text"], raw_content)
        self.assertNotIn("\ufffd", result.context["variables"]["file_content"]["text"])

    def test_workflow_file_extract_node_prefers_decoded_data_url_over_broken_text_preview(self) -> None:
        raw_content = "北京客户清单,WPS365-文档平台\n张三,合同审批"
        encoded_content = base64.b64encode(raw_content.encode("gb18030")).decode("ascii")
        broken_preview = raw_content.encode("gb18030").decode("utf-8", errors="replace")
        definition = file_extract_definition()

        result = execute_workflow(
            definition,
            {
                "document": {
                    "type": "file",
                    "name": "客户清单.csv",
                    "mime_type": "text/csv",
                    "text": broken_preview,
                    "data_url": f"data:text/csv;base64,{encoded_content}",
                }
            },
            llm_executor=lambda request: WorkflowLLMResult(answer=""),
        )

        self.assertEqual(result.context["variables"]["file_content"]["text"], raw_content)

    def test_workflow_file_extract_node_accepts_external_extractor(self) -> None:
        definition = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {
                    "id": "file_extract_1",
                    "type": "file_extraction",
                    "data": {"input": "{{document}}", "output_key": "file_content", "max_chars": 100},
                },
                {"id": "end", "type": "end", "data": {"output": "{{file_content.file_count}}" }},
            ],
            "edges": [
                {"source": "start", "target": "file_extract_1"},
                {"source": "file_extract_1", "target": "end"},
            ],
        }
        requests: list[WorkflowFileExtractRequest] = []

        def fake_file_extractor(request: WorkflowFileExtractRequest) -> WorkflowFileExtractResult:
            requests.append(request)
            return WorkflowFileExtractResult(
                text="外部提取结果",
                files=[{"name": "contract.pdf", "mime_type": "application/pdf", "text": "外部提取结果"}],
                file_count=1,
            )

        result = execute_workflow(
            definition,
            {"document": {"type": "file", "name": "contract.pdf", "file_ref": "file_1"}},
            llm_executor=lambda request: WorkflowLLMResult(answer=""),
            file_extractor=fake_file_extractor,
        )

        self.assertEqual(result.answer, "1")
        self.assertEqual(requests[0].node_id, "file_extract_1")
        self.assertEqual(requests[0].value["file_ref"], "file_1")
        self.assertEqual(result.context["variables"]["file_content"]["text"], "外部提取结果")

    def test_workflow_file_extract_node_parses_pdf_data_url(self) -> None:
        definition = file_extract_definition()
        pdf_data_url = "data:application/pdf;base64," + base64.b64encode(minimal_pdf_bytes("PDF 内容")).decode("ascii")

        result = execute_workflow(
            definition,
            {"document": {"type": "file", "name": "sample.pdf", "mime_type": "application/pdf", "data_url": pdf_data_url}},
            llm_executor=lambda request: WorkflowLLMResult(answer=""),
        )

        self.assertIn("PDF", result.context["variables"]["file_content"]["text"])

    def test_workflow_file_extract_node_parses_docx_data_url(self) -> None:
        definition = file_extract_definition()
        docx_data_url = "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64," + base64.b64encode(
            minimal_docx_bytes(["第一段", "第二段"])
        ).decode("ascii")

        result = execute_workflow(
            definition,
            {"document": {"type": "file", "name": "sample.docx", "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "data_url": docx_data_url}},
            llm_executor=lambda request: WorkflowLLMResult(answer=""),
        )

        self.assertEqual(result.context["variables"]["file_content"]["text"], "第一段\n第二段")

    def test_workflow_file_extract_node_parses_xlsx_data_url(self) -> None:
        definition = file_extract_definition()
        xlsx_data_url = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + base64.b64encode(
            minimal_xlsx_bytes([["姓名", "金额"], ["张三", 12]])
        ).decode("ascii")

        result = execute_workflow(
            definition,
            {"document": {"type": "file", "name": "sample.xlsx", "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "data_url": xlsx_data_url}},
            llm_executor=lambda request: WorkflowLLMResult(answer=""),
        )

        self.assertIn("## Sheet", result.context["variables"]["file_content"]["text"])
        self.assertIn("姓名\t金额", result.context["variables"]["file_content"]["text"])
        self.assertIn("张三\t12", result.context["variables"]["file_content"]["text"])

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


def file_extract_definition() -> dict[str, object]:
    return {
        "nodes": [
            {"id": "start", "type": "start", "data": {}},
            {
                "id": "file_extract_1",
                "type": "file_extract",
                "data": {"input": "{{document}}", "output_key": "file_content", "max_chars": 2000},
            },
            {"id": "end", "type": "end", "data": {"output": "{{file_content.text}}" }},
        ],
        "edges": [
            {"source": "start", "target": "file_extract_1"},
            {"source": "file_extract_1", "target": "end"},
        ],
    }


def minimal_docx_bytes(paragraphs: list[str]) -> bytes:
    document_body = "".join(
        f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{document_body}</w:body>"
        "</w:document>"
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def minimal_xlsx_bytes(rows: list[list[object]]) -> bytes:
    import openpyxl

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    for row in rows:
        worksheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def minimal_pdf_bytes(text: str) -> bytes:
    safe_text = text.encode("latin-1", errors="ignore").decode("latin-1")
    stream = f"BT /F1 24 Tf 72 720 Td ({safe_text}) Tj ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(stream.encode('latin-1'))} >> stream\n{stream}\nendstream endobj",
    ]
    content = "%PDF-1.4\n"
    offsets = [0]
    for item in objects:
        offsets.append(len(content.encode("latin-1")))
        content += item + "\n"
    xref_offset = len(content.encode("latin-1"))
    content += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        content += f"{offset:010d} 00000 n \n"
    content += f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    return content.encode("latin-1")


if __name__ == "__main__":
    unittest.main()
