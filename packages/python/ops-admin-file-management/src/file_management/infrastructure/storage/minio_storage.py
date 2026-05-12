from __future__ import annotations

import hashlib
from typing import BinaryIO

from file_management.application.ports import DownloadObject, StoredObject
from file_management.domain.models import STORAGE_PROVIDER_MINIO, StorageProfile


class MinioObjectStorage:
    def save(self, *, profile: StorageProfile, key: str, content: BinaryIO, content_type: str) -> StoredObject:
        client = self._client(profile)
        digest = hashlib.sha256()
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = content.read(1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            digest.update(chunk)
        from io import BytesIO

        client.put_object(profile.bucket, key, BytesIO(b"".join(chunks)), length=size, content_type=content_type)
        return StoredObject(
            provider=STORAGE_PROVIDER_MINIO,
            bucket=profile.bucket,
            key=key,
            size_bytes=size,
            sha256=digest.hexdigest(),
        )

    def open_for_read(self, *, profile: StorageProfile, key: str) -> DownloadObject:
        client = self._client(profile)
        response = client.get_object(profile.bucket, key)
        return DownloadObject(stream=response, content_type="application/octet-stream")

    def delete(self, *, profile: StorageProfile, key: str) -> None:
        self._client(profile).remove_object(profile.bucket, key)

    def exists(self, *, profile: StorageProfile, key: str) -> bool:
        try:
            self._client(profile).stat_object(profile.bucket, key)
        except Exception:
            return False
        return True

    def test_connection(self, *, profile: StorageProfile) -> dict[str, object]:
        client = self._client(profile)
        exists = client.bucket_exists(profile.bucket)
        return {"ok": bool(exists), "provider": profile.provider, "bucket": profile.bucket}

    def _client(self, profile: StorageProfile):
        try:
            from minio import Minio
        except ImportError as exc:
            raise RuntimeError("minio package is not installed; install ops-admin-file-management[minio]") from exc
        endpoint = profile.endpoint.removeprefix("https://").removeprefix("http://")
        return Minio(
            endpoint,
            access_key=profile.access_key_id,
            secret_key=profile.secret_access_key,
            secure=profile.tls_enabled,
            region=profile.region or None,
        )
