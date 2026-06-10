from __future__ import annotations

from typing import Any, BinaryIO

from fastapi import HTTPException

from ai_runtime_core.workflow_runtime import WorkflowFileExtractRequest
from ai_runtime_core.workflow_runtime import WorkflowFileExtractResult
from ai_runtime_core.workflow_runtime import extract_file_content_payload
from ai_applications.application.ports import RuntimeFileReadPort
from ai_applications.application.ports import RuntimeFileUploadPort


class RuntimeFileUploadUnavailable(RuntimeError):
    pass


class RuntimeFileReadUnavailable(RuntimeError):
    pass


_runtime_file_upload_port: RuntimeFileUploadPort | None = None
_runtime_file_read_port: RuntimeFileReadPort | None = None


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


class UnavailableRuntimeFileReadPort:
    def read_runtime_file(
        self,
        *,
        current_user: dict[str, Any],
        file_id: int | None,
        file_ref: str | None,
    ) -> dict[str, Any]:
        raise RuntimeFileReadUnavailable("runtime file read is not configured")


def configure_runtime_file_upload_port(port: RuntimeFileUploadPort | None) -> None:
    global _runtime_file_upload_port
    _runtime_file_upload_port = port or UnavailableRuntimeFileUploadPort()


def configure_runtime_file_read_port(port: RuntimeFileReadPort | None) -> None:
    global _runtime_file_read_port
    _runtime_file_read_port = port or UnavailableRuntimeFileReadPort()


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


def runtime_file_read_port() -> RuntimeFileReadPort:
    return _runtime_file_read_port or UnavailableRuntimeFileReadPort()


def workflow_file_extractor(
    request: WorkflowFileExtractRequest,
    *,
    current_user: dict[str, Any] | None,
) -> WorkflowFileExtractResult:
    source_value = request.value
    if not current_user or not runtime_value_needs_file_lookup(source_value):
        payload = extract_file_content_payload(source_value, max_chars=request.max_chars)
        return WorkflowFileExtractResult(
            text=str(payload.get("text") or ""),
            files=payload.get("files") if isinstance(payload.get("files"), list) else [],
            file_count=int(payload.get("file_count") or 0),
            truncated=bool(payload.get("truncated")),
        )
    resolved_value = hydrate_runtime_file_value(source_value, current_user=current_user)
    payload = extract_file_content_payload(resolved_value, max_chars=request.max_chars)
    return WorkflowFileExtractResult(
        text=str(payload.get("text") or ""),
        files=payload.get("files") if isinstance(payload.get("files"), list) else [],
        file_count=int(payload.get("file_count") or 0),
        truncated=bool(payload.get("truncated")),
    )


def runtime_value_needs_file_lookup(value: Any) -> bool:
    for item in runtime_file_items(value):
        if not isinstance(item, dict):
            continue
        if item.get("text") or item.get("content") or item.get("data_url"):
            continue
        if item.get("file_id") not in (None, "") or str(item.get("file_ref") or "").strip():
            return True
    return False


def hydrate_runtime_file_value(value: Any, *, current_user: dict[str, Any]) -> Any:
    if isinstance(value, list):
        return [hydrate_runtime_file_value(item, current_user=current_user) for item in value]
    if not isinstance(value, dict):
        return value
    if isinstance(value.get("files"), list):
        result = dict(value)
        result["files"] = [hydrate_runtime_file_item(item, current_user=current_user) for item in value["files"]]
        return result
    if isinstance(value.get("items"), list) and not runtime_media_like_file_record(value):
        result = dict(value)
        result["items"] = [hydrate_runtime_file_item(item, current_user=current_user) for item in value["items"]]
        return result
    return hydrate_runtime_file_item(value, current_user=current_user)


def hydrate_runtime_file_item(value: Any, *, current_user: dict[str, Any]) -> Any:
    if not isinstance(value, dict):
        return value
    if value.get("text") or value.get("content") or value.get("data_url"):
        return value
    file_id = parse_runtime_file_id(value.get("file_id"))
    file_ref = str(value.get("file_ref") or "").strip() or None
    if file_id is None and not file_ref:
        return value
    resolved = runtime_file_read_port().read_runtime_file(
        current_user=current_user,
        file_id=file_id,
        file_ref=file_ref,
    )
    result = dict(value)
    for key in ("name", "mime_type", "size", "text", "data_url", "file_ref", "file_id"):
        if resolved.get(key) not in (None, ""):
            result[key] = resolved.get(key)
    return result


def parse_runtime_file_id(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def runtime_file_items(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, "")]
    if isinstance(value, dict):
        if isinstance(value.get("files"), list):
            return value["files"]
        if isinstance(value.get("items"), list) and not runtime_media_like_file_record(value):
            return value["items"]
    return [value]


def runtime_media_like_file_record(value: dict[str, Any]) -> bool:
    return any(key in value for key in ("type", "name", "mime_type", "data_url", "text", "file_ref", "file_id"))
