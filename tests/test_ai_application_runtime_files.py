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
