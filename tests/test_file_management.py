from __future__ import annotations

import hashlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from file_management.application import services
from file_management.application.ports import DownloadObject, StoredObject
from file_management.domain.models import STORAGE_PROVIDER_MINIO, StorageProfile


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def save(self, *, profile: StorageProfile, key: str, content: io.BytesIO, content_type: str) -> StoredObject:
        data = content.read()
        self.objects[key] = data
        return StoredObject(
            provider=STORAGE_PROVIDER_MINIO,
            bucket=profile.bucket,
            key=key,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )

    def open_for_read(self, *, profile: StorageProfile, key: str) -> DownloadObject:
        return DownloadObject(stream=io.BytesIO(self.objects[key]), size_bytes=len(self.objects[key]))

    def delete(self, *, profile: StorageProfile, key: str) -> None:
        self.objects.pop(key, None)

    def exists(self, *, profile: StorageProfile, key: str) -> bool:
        return key in self.objects

    def test_connection(self, *, profile: StorageProfile) -> dict[str, object]:
        return {"ok": True, "provider": profile.provider, "bucket": profile.bucket}


class FileManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "files.db"
        self.env_patch = mock.patch.dict(
            "os.environ",
            {
                "FG_AGENT_DATABASE_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-database.json"),
                "FG_AGENT_DATABASE_URL": "",
                "SUPABASE_DB_URL": "",
                "DATABASE_URL": "",
                "FG_AGENT_DB_PATH": str(self.db_path),
            },
            clear=False,
        )
        self.env_patch.start()
        self.storage = MemoryStorage()
        services.configure_storage(self.storage)
        self.current_user = {
            "id": 10,
            "username": "owner",
            "current_tenant": {"id": 7, "tenant_key": "tenant-a", "name": "Tenant A"},
            "tenant_id": 7,
        }
        self.admin_user = {
            "id": 1,
            "username": "admin",
            "current_tenant": {"id": 1, "tenant_key": "platform", "name": "Platform"},
            "tenant_id": 1,
            "is_platform_admin": True,
        }
        self.initialize_db()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def initialize_db(self) -> None:
        from file_management.infrastructure.persistence.bootstrap import ensure_file_management_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_file_management_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def create_default_profile(self) -> dict[str, object]:
        response = services.save_storage_profile(
            {
                "provider": "minio",
                "name": "Default MinIO",
                "endpoint": "http://localhost:9000",
                "bucket": "ops-files",
                "access_key_id": "minio",
                "secret_access_key": "miniopass",
                "is_default": True,
                "enabled": True,
            },
            self.admin_user,
        )
        return response["item"]

    def test_storage_profile_masks_secret_and_rejects_unsupported_provider(self) -> None:
        profile = self.create_default_profile()

        self.assertTrue(profile["secret_configured"])
        self.assertNotIn("secret_access_key", profile)

        with self.assertRaises(Exception) as caught:
            services.save_storage_profile(
                {
                    "provider": "aliyun_oss",
                    "name": "OSS",
                    "endpoint": "oss-cn.example.aliyuncs.com",
                    "bucket": "bucket",
                },
                self.admin_user,
            )

        self.assertEqual(getattr(caught.exception, "status_code", None), 400)

    def test_upload_download_search_and_delete_file(self) -> None:
        self.create_default_profile()
        library = services.save_library({"name": "Contracts"}, self.current_user)["item"]
        services.save_quota(
            7,
            {
                "quota_bytes": 1000,
                "max_file_size_bytes": 100,
                "allowed_mime_types": ["text/plain"],
                "blocked_extensions": ["exe"],
                "enabled": True,
            },
            self.admin_user,
        )

        upload = services.upload_file(
            current_user=self.current_user,
            filename="contract.txt",
            content_type="text/plain",
            stream=io.BytesIO(b"hello"),
            library_id=int(library["id"]),
            visibility="tenant",
            metadata={"source": "test"},
        )["item"]

        self.assertEqual(upload["original_name"], "contract.txt")
        self.assertEqual(upload["size_bytes"], 5)
        self.assertNotIn("storage_key", upload)
        self.assertEqual(services.list_index_jobs(page=1, page_size=20, current_user=self.current_user)["pagination"]["total"], 1)

        files = services.list_files(page=1, page_size=20, current_user=self.current_user)
        self.assertEqual(files["pagination"]["total"], 1)

        search = services.search_files(page=1, page_size=20, keyword="contract", current_user=self.current_user)
        self.assertEqual(search["pagination"]["total"], 1)

        item, download = services.download_file(int(upload["id"]), self.current_user)
        self.assertEqual(item.original_name, "contract.txt")
        self.assertEqual(download.stream.read(), b"hello")
        logs = services.list_access_logs(page=1, page_size=20, current_user=self.current_user)
        self.assertEqual(logs["pagination"]["total"], 2)

        reindex = services.reindex_file(int(upload["id"]), self.current_user)["item"]
        self.assertEqual(reindex["job_type"], "manual_reindex")
        self.assertEqual(reindex["status"], "succeeded")

        delete = services.delete_file(int(upload["id"]), self.current_user)
        self.assertTrue(delete["deleted"])
        after = services.list_files(page=1, page_size=20, current_user=self.current_user)
        self.assertEqual(after["pagination"]["total"], 0)
        self.assertEqual(services.list_index_jobs(page=1, page_size=20, current_user=self.current_user)["pagination"]["total"], 3)

    def test_provider_options_expose_reserved_providers(self) -> None:
        options = services.storage_provider_options()["items"]
        by_provider = {str(item["provider"]): item for item in options}

        self.assertTrue(by_provider["minio"]["supported"])
        self.assertFalse(by_provider["tencent_cos"]["supported"])
        self.assertFalse(by_provider["aliyun_oss"]["supported"])

    def test_quota_blocks_oversized_file(self) -> None:
        self.create_default_profile()
        services.save_quota(
            7,
            {
                "quota_bytes": 3,
                "max_file_size_bytes": 3,
                "allowed_mime_types": ["text/plain"],
                "blocked_extensions": [],
                "enabled": True,
            },
            self.admin_user,
        )

        with self.assertRaises(Exception) as caught:
            services.upload_file(
                current_user=self.current_user,
                filename="large.txt",
                content_type="text/plain",
                stream=io.BytesIO(b"large"),
                library_id=None,
                visibility="tenant",
                metadata={},
            )

        self.assertEqual(getattr(caught.exception, "status_code", None), 400)
        self.assertEqual(services.list_files(page=1, page_size=20, current_user=self.current_user)["pagination"]["total"], 0)

    def test_tenant_isolation_for_file_reads(self) -> None:
        self.create_default_profile()
        upload = services.upload_file(
            current_user=self.current_user,
            filename="private.txt",
            content_type="text/plain",
            stream=io.BytesIO(b"secret"),
            library_id=None,
            visibility="tenant",
            metadata={},
        )["item"]
        other_user = {
            "id": 11,
            "username": "other",
            "current_tenant": {"id": 8, "tenant_key": "tenant-b", "name": "Tenant B"},
            "tenant_id": 8,
        }

        with self.assertRaises(Exception) as caught:
            services.get_file(int(upload["id"]), other_user)

        self.assertEqual(getattr(caught.exception, "status_code", None), 404)


if __name__ == "__main__":
    unittest.main()
