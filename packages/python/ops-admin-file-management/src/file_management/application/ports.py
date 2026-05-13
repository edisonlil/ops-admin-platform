from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Literal, Protocol

from file_management.domain.models import ManagedFile, StorageProfile


@dataclass(frozen=True)
class StoredObject:
    provider: str
    bucket: str
    key: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class DownloadObject:
    stream: BinaryIO
    size_bytes: int | None = None
    content_type: str | None = None


PreviewMode = Literal["image", "pdf", "text", "audio", "video", "external", "unsupported"]


@dataclass(frozen=True)
class FilePreview:
    previewable: bool
    engine: str
    mode: PreviewMode
    mime_type: str
    reason: str = ""
    url: str = ""
    max_inline_bytes: int | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "previewable": self.previewable,
            "engine": self.engine,
            "mode": self.mode,
            "mime_type": self.mime_type,
            "reason": self.reason,
            "url": self.url,
        }
        if self.max_inline_bytes is not None:
            payload["max_inline_bytes"] = self.max_inline_bytes
        return payload


class StoragePort(Protocol):
    def save(self, *, profile: StorageProfile, key: str, content: BinaryIO, content_type: str) -> StoredObject:
        ...

    def open_for_read(self, *, profile: StorageProfile, key: str) -> DownloadObject:
        ...

    def delete(self, *, profile: StorageProfile, key: str) -> None:
        ...

    def exists(self, *, profile: StorageProfile, key: str) -> bool:
        ...

    def test_connection(self, *, profile: StorageProfile) -> dict[str, object]:
        ...


class FileIndexerPort(Protocol):
    def index_file(self, file_id: int) -> None:
        ...

    def remove_file(self, file_id: int) -> None:
        ...


class PreviewProviderPort(Protocol):
    engine: str

    def metadata_for(self, file: ManagedFile) -> FilePreview:
        ...
