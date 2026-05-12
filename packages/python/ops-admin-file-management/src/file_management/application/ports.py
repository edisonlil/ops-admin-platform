from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol

from file_management.domain.models import StorageProfile


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
