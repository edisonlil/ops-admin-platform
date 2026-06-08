from __future__ import annotations

from typing import Any, BinaryIO

from fastapi import HTTPException

from ai_applications.application.ports import RuntimeFileUploadPort


class RuntimeFileUploadUnavailable(RuntimeError):
    pass


_runtime_file_upload_port: RuntimeFileUploadPort | None = None


class UnavailableRuntimeFileUploadPort:
    def upload_runtime_file(
        self,
        *,
        current_user: dict[str, Any],
        filename: str,
        content_type: str,
        stream: BinaryIO,
        visibility: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        raise RuntimeFileUploadUnavailable("runtime file upload is not configured")


def configure_runtime_file_upload_port(port: RuntimeFileUploadPort | None) -> None:
    global _runtime_file_upload_port
    _runtime_file_upload_port = port or UnavailableRuntimeFileUploadPort()


def upload_runtime_variable_file(
    *,
    current_user: dict[str, Any],
    filename: str,
    content_type: str,
    stream: BinaryIO,
    visibility: str = "tenant",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return runtime_file_upload_port().upload_runtime_file(
            current_user=current_user,
            filename=filename,
            content_type=content_type,
            stream=stream,
            visibility=visibility,
            metadata=metadata or {},
        )
    except RuntimeFileUploadUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def runtime_file_upload_port() -> RuntimeFileUploadPort:
    return _runtime_file_upload_port or UnavailableRuntimeFileUploadPort()
