"""组合层：为 ai_applications 注入跨上下文适配器。

ai_applications 不得直接 import file_management；文件上传能力在此通过 Port 接线。
"""
from __future__ import annotations

from typing import Any, BinaryIO


def wire_ai_applications_dependencies() -> None:
    from ai_applications.application.runtime_files import configure_runtime_file_upload_port

    try:
        from file_management.application import services as file_services
    except ImportError:
        configure_runtime_file_upload_port(None)
        return

    configure_runtime_file_upload_port(FileManagementRuntimeFileUploadAdapter(file_services))


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
