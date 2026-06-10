from __future__ import annotations

from typing import Any, BinaryIO, Protocol


class AIApplicationsRepository(Protocol):
    def __getattr__(self, name: str) -> Any: ...
    def require_ai_applications_schema(self, *args: Any, **kwargs: Any) -> Any: ...
    def require_ai_agent_schema(self, *args: Any, **kwargs: Any) -> Any: ...
    def require_prompt_runtime_trace_detail_schema(self, *args: Any, **kwargs: Any) -> Any: ...


class RuntimeFileUploadPort(Protocol):
    """将运行变量文件委托给外部文件能力；ai_applications 只保留引用，不耦合文件领域实现。"""

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
        ...


class RuntimeFileReadPort(Protocol):
    """按 file_ref/file_id 读取运行变量文件内容；用于 Workflow 等运行时回填文件正文。"""

    def read_runtime_file(
        self,
        *,
        current_user: dict[str, Any],
        file_id: int | None,
        file_ref: str | None,
    ) -> dict[str, Any]:
        ...

