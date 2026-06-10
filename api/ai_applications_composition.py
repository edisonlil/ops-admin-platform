"""组合层：为 ai_applications 注入跨上下文适配器。

ai_applications 不得直接 import file_management；文件上传能力在此通过 Port 接线。
"""
from __future__ import annotations

from io import BytesIO
from typing import Any, BinaryIO


def wire_ai_applications_dependencies() -> None:
    from ai_applications.application.runtime_files import configure_runtime_file_read_port
    from ai_applications.application.runtime_files import configure_runtime_file_upload_port

    try:
        from file_management.application import services as file_services
    except ImportError:
        configure_runtime_file_upload_port(None)
        configure_runtime_file_read_port(None)
        return

    configure_runtime_file_upload_port(FileManagementRuntimeFileUploadAdapter(file_services))
    configure_runtime_file_read_port(FileManagementRuntimeFileReadAdapter(file_services))


class FileManagementRuntimeFileUploadAdapter:
    def __init__(self, file_services: Any) -> None:
        self._file_services = file_services

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
        payload = self._file_services.upload_file(
            current_user=current_user,
            filename=filename,
            content_type=content_type,
            stream=stream,
            library_id=None,
            folder_id=None,
            visibility=visibility,
            metadata=metadata,
            tag_codes=[],
        )
        item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
        file_id = int(item.get("id") or 0)
        return {
            "file_id": file_id,
            "file_ref": f"file_{file_id}" if file_id else None,
            "sha256": str(item.get("sha256") or ""),
            "name": str(item.get("display_name") or item.get("original_name") or filename),
            "mime_type": str(item.get("mime_type") or content_type or "application/octet-stream"),
            "size": int(item.get("size_bytes") or 0),
            "storage_status": "stored" if file_id else "unavailable",
        }


class FileManagementRuntimeFileReadAdapter:
    def __init__(self, file_services: Any) -> None:
        self._file_services = file_services

    def read_runtime_file(
        self,
        *,
        current_user: dict[str, Any],
        file_id: int | None,
        file_ref: str | None,
    ) -> dict[str, Any]:
        resolved_file_id = file_id or parse_file_ref_id(file_ref)
        if not resolved_file_id:
            return {}
        item, download = self._file_services.download_file(resolved_file_id, current_user)
        content = read_download_bytes(download.stream)
        return {
            "file_id": int(getattr(item, "id", 0) or resolved_file_id),
            "file_ref": f"file_{int(getattr(item, 'id', 0) or resolved_file_id)}",
            "name": str(getattr(item, "original_name", "") or ""),
            "mime_type": str(getattr(item, "mime_type", "") or "application/octet-stream"),
            "size": int(getattr(item, "size_bytes", 0) or len(content)),
            "data_url": build_runtime_file_data_url(content, str(getattr(item, "mime_type", "") or "")),
        }


def parse_file_ref_id(file_ref: str | None) -> int | None:
    text = str(file_ref or "").strip().lower()
    if not text.startswith("file_"):
        return None
    try:
        parsed = int(text.split("_", 1)[1])
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def read_download_bytes(stream: BinaryIO) -> bytes:
    data = stream.read()
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode("utf-8")
    return BytesIO().getvalue()


def build_runtime_file_data_url(content: bytes, mime_type: str) -> str:
    import base64

    payload = base64.b64encode(content).decode("ascii")
    effective_mime_type = (mime_type or "application/octet-stream").strip() or "application/octet-stream"
    return f"data:{effective_mime_type};base64,{payload}"
