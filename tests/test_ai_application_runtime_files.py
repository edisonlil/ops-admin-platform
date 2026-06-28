from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import HTTPException

from ai_applications.application import runtime_files


class FakeRuntimeFileUploadPort:
    def upload_runtime_file(self, **kwargs):
        return {
            "file_id": 42,
            "file_ref": "file_42",
            "sha256": "abc",
            "name": kwargs["filename"],
            "mime_type": kwargs["content_type"],
            "size": 3,
            "storage_status": "stored",
        }


class FakeRuntimeFileReadPort:
    def read_runtime_file(self, **kwargs):
        return {
            "file_id": kwargs["file_id"] or 42,
            "file_ref": kwargs["file_ref"] or "file_42",
            "name": "demo.txt",
            "mime_type": "text/plain",
            "size": 6,
            "text": "已解析内容",
        }


class FakeRuntimeBinaryFileReadPort:
    def read_runtime_file(self, **kwargs):
        return {
            "file_id": kwargs["file_id"] or 7,
            "file_ref": kwargs["file_ref"] or "file_7",
            "name": "spec.pdf",
            "mime_type": "application/pdf",
            "size": 7,
            "data_url": "data:application/pdf;base64,JVBERi0xLjc=",
        }


def test_upload_runtime_variable_file_uses_configured_port() -> None:
    runtime_files.configure_runtime_file_upload_port(FakeRuntimeFileUploadPort())
    result = runtime_files.upload_runtime_variable_file(
        current_user={"tenant_id": 1, "user_id": 1},
        filename="demo.pdf",
        content_type="application/pdf",
        stream=BytesIO(b"pdf"),
    )
    assert result["file_ref"] == "file_42"
    assert result["name"] == "demo.pdf"


def test_upload_runtime_variable_file_reports_unavailable_port() -> None:
    runtime_files.configure_runtime_file_upload_port(None)
    with pytest.raises(HTTPException) as exc:
        runtime_files.upload_runtime_variable_file(
            current_user={"tenant_id": 1, "user_id": 1},
            filename="demo.pdf",
            content_type="application/pdf",
            stream=BytesIO(b"pdf"),
        )
    assert exc.value.status_code == 503


def test_workflow_file_extractor_hydrates_file_ref_content() -> None:
    runtime_files.configure_runtime_file_read_port(FakeRuntimeFileReadPort())
    result = runtime_files.workflow_file_extractor(
        runtime_files.WorkflowFileExtractRequest(
            node_id="file_extract_1",
            value={"type": "file", "name": "demo.txt", "mime_type": "text/plain", "file_ref": "file_42", "file_id": 42},
            output_key="file_content",
            max_chars=100,
        ),
        current_user={"tenant_id": 1, "user_id": 1},
    )
    assert result.text == "已解析内容"
    assert result.files[0]["file_ref"] == "file_42"
    assert result.files[0]["text"] == "已解析内容"


def test_hydrate_runtime_file_item_populates_binary_data_url() -> None:
    runtime_files.configure_runtime_file_read_port(FakeRuntimeBinaryFileReadPort())
    result = runtime_files.hydrate_runtime_file_item(
        {"type": "file", "name": "spec.pdf", "file_ref": "file_7"},
        current_user={"tenant_id": 1, "user_id": 1},
    )
    assert result["file_ref"] == "file_7"
    assert result["data_url"] == "data:application/pdf;base64,JVBERi0xLjc="
