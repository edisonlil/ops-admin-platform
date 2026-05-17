from __future__ import annotations

import hashlib
import io
import sqlite3
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from file_management.application import services
from file_management.application.ports import DownloadObject, StoredObject
from file_management.domain.models import STORAGE_PROVIDER_MINIO, StorageProfile


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    def save(self, *, profile: StorageProfile, key: str, content: io.BytesIO, content_type: str) -> StoredObject:
        data = content.read()
        self.objects[key] = data
        self.content_types[key] = content_type
        return StoredObject(
            provider=STORAGE_PROVIDER_MINIO,
            bucket=profile.bucket,
            key=key,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )

    def open_for_read(self, *, profile: StorageProfile, key: str) -> DownloadObject:
        return DownloadObject(
            stream=io.BytesIO(self.objects[key]),
            size_bytes=len(self.objects[key]),
            content_type=self.content_types.get(key),
        )

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
                "OPS_ADMIN_APPLICATION_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-application.json"),
                "OPS_ADMIN_PUBLIC_API_BASE_URL": "http://testserver",
                "OPS_ADMIN_PUBLIC_API_URL_PREFIX": "/api",
                "OPS_ADMIN_FILE_PREVIEW_SECRET": "test-preview-secret",
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
        folder = services.save_folder(
            {"library_id": int(library["id"]), "name": "2026 Contracts"},
            self.current_user,
        )["item"]
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
            folder_id=int(folder["id"]),
            visibility="tenant",
            metadata={"source": "test"},
        )["item"]

        self.assertEqual(upload["original_name"], "contract.txt")
        self.assertEqual(upload["folder_id"], int(folder["id"]))
        self.assertEqual(upload["size_bytes"], 5)
        self.assertNotIn("storage_key", upload)
        self.assertEqual(services.list_index_jobs(page=1, page_size=20, current_user=self.current_user)["pagination"]["total"], 1)

        files = services.list_files(
            page=1,
            page_size=20,
            current_user=self.current_user,
            library_id=int(library["id"]),
            folder_id=int(folder["id"]),
            current_folder_only=True,
        )
        self.assertEqual(files["pagination"]["total"], 1)
        workspace = services.list_workspace(
            current_user=self.current_user,
            library_id=int(library["id"]),
            folder_id=int(folder["id"]),
        )
        self.assertEqual(len(workspace["breadcrumbs"]), 1)
        self.assertEqual(workspace["breadcrumbs"][0]["name"], "2026 Contracts")
        self.assertEqual(len(workspace["files"]), 1)
        self.assertEqual(workspace["current_usage"]["used_bytes"], 5)

        search = services.search_files(page=1, page_size=20, keyword="contract", current_user=self.current_user)
        self.assertEqual(search["pagination"]["total"], 1)

        item, download = services.download_file(int(upload["id"]), self.current_user)
        self.assertEqual(item.original_name, "contract.txt")
        self.assertEqual(download.stream.read(), b"hello")
        preview_metadata = services.get_file_preview_metadata(int(upload["id"]), self.current_user)
        self.assertTrue(preview_metadata["preview"]["previewable"])
        self.assertEqual(preview_metadata["preview"]["engine"], "native")
        self.assertEqual(preview_metadata["preview"]["mode"], "text")
        preview_item, preview_download, preview = services.preview_file(int(upload["id"]), self.current_user)
        self.assertEqual(preview_item.original_name, "contract.txt")
        self.assertEqual(preview_download.stream.read(), b"hello")
        self.assertEqual(preview["mode"], "text")
        logs = services.list_access_logs(page=1, page_size=20, current_user=self.current_user)
        self.assertEqual(logs["pagination"]["total"], 3)
        preview_logs = services.list_access_logs(page=1, page_size=20, current_user=self.current_user, action="preview")
        self.assertEqual(preview_logs["pagination"]["total"], 1)

        reindex = services.reindex_file(int(upload["id"]), self.current_user)["item"]
        self.assertEqual(reindex["job_type"], "manual_reindex")
        self.assertEqual(reindex["status"], "succeeded")

        delete = services.delete_file(int(upload["id"]), self.current_user)
        self.assertTrue(delete["deleted"])
        after = services.list_files(page=1, page_size=20, current_user=self.current_user)
        self.assertEqual(after["pagination"]["total"], 0)
        quota_after_delete = services.quota_for_tenant(7)
        self.assertEqual(quota_after_delete["usage"]["used_bytes"], 0)
        self.assertEqual(quota_after_delete["usage"]["file_count"], 0)
        workspace_after_delete = services.list_workspace(
            current_user=self.current_user,
            library_id=int(library["id"]),
            folder_id=int(folder["id"]),
        )
        self.assertEqual(workspace_after_delete["current_usage"]["used_bytes"], 0)
        self.assertEqual(services.list_index_jobs(page=1, page_size=20, current_user=self.current_user)["pagination"]["total"], 3)
        deleted_folder = services.delete_folder(int(folder["id"]), self.current_user)
        self.assertTrue(deleted_folder["deleted"])

    def test_native_preview_rejects_unsupported_file_type(self) -> None:
        self.create_default_profile()
        upload = services.upload_file(
            current_user=self.current_user,
            filename="archive.zip",
            content_type="application/zip",
            stream=io.BytesIO(b"zip"),
            library_id=None,
            visibility="tenant",
            metadata={},
        )["item"]

        metadata = services.get_file_preview_metadata(int(upload["id"]), self.current_user)

        self.assertFalse(metadata["preview"]["previewable"])
        self.assertEqual(metadata["preview"]["mode"], "unsupported")
        self.assertEqual(metadata["preview"]["reason"], "unsupported_mime_type")
        with self.assertRaises(Exception) as caught:
            services.preview_file(int(upload["id"]), self.current_user)
        self.assertEqual(getattr(caught.exception, "status_code", None), 415)

    def test_external_preview_profile_builds_signed_kkfileview_url(self) -> None:
        self.create_default_profile()
        services.save_preview_profile(
            {
                "provider": "kkfileview",
                "name": "Default kkFileView",
                "base_url": "http://kkfileview.local",
                "enabled": True,
                "is_default": True,
                "supported_extensions": ["docx"],
                "config": {"source_url_ttl_seconds": 300, "url_param_name": "url"},
            },
            self.admin_user,
        )
        upload = services.upload_file(
            current_user=self.current_user,
            filename="proposal.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            stream=io.BytesIO(b"office-doc"),
            library_id=None,
            visibility="tenant",
            metadata={},
        )["item"]

        metadata = services.get_file_preview_metadata(int(upload["id"]), self.current_user)

        preview = metadata["preview"]
        self.assertTrue(preview["previewable"])
        self.assertEqual(preview["engine"], "kkfileview")
        self.assertEqual(preview["mode"], "external")
        parsed = urllib.parse.urlparse(str(preview["url"]))
        self.assertEqual(parsed.scheme, "http")
        self.assertEqual(parsed.netloc, "kkfileview.local")
        self.assertEqual(parsed.path, "/onlinePreview")
        source_url = urllib.parse.parse_qs(parsed.query)["url"][0]
        source = urllib.parse.urlparse(source_url)
        self.assertEqual(source_url.split("?", 1)[0], f"http://testserver/api/files/{upload['id']}/preview-source")
        query = urllib.parse.parse_qs(source.query)
        item, download = services.preview_source_file(
            int(upload["id"]),
            expires=int(query["expires"][0]),
            signature=query["signature"][0],
        )
        self.assertEqual(item.original_name, "proposal.docx")
        self.assertEqual(download.stream.read(), b"office-doc")

    def test_preview_public_url_reads_application_config_when_env_is_empty(self) -> None:
        with (
            mock.patch.dict(
                "os.environ",
                {"OPS_ADMIN_PUBLIC_API_BASE_URL": "", "OPS_ADMIN_PUBLIC_API_URL_PREFIX": ""},
                clear=False,
            ),
            mock.patch.object(
                services,
                "load_application_config",
                return_value={
                    "file_management": {
                        "preview": {
                            "public_api_base_url": "http://files.example.test:8000",
                            "public_api_url_prefix": "/gateway/api",
                        }
                    }
                },
            ),
        ):
            self.assertEqual(services.external_base_url(), "http://files.example.test:8000")
            self.assertEqual(services.external_url_prefix(), "/gateway/api")

    def test_preview_public_url_env_overrides_config_file(self) -> None:
        with (
            mock.patch.dict(
                "os.environ",
                {
                    "OPS_ADMIN_PUBLIC_API_BASE_URL": "http://env.example.test:9000",
                    "OPS_ADMIN_PUBLIC_API_URL_PREFIX": "/env-api",
                },
                clear=False,
            ),
            mock.patch.object(
                services,
                "load_application_config",
                return_value={
                    "file_management": {
                        "preview": {
                            "public_api_base_url": "http://files.example.test:8000",
                            "public_api_url_prefix": "/gateway/api",
                        }
                    }
                },
            ),
        ):
            self.assertEqual(services.external_base_url(), "http://env.example.test:9000")
            self.assertEqual(services.external_url_prefix(), "/env-api")

    def test_folder_rejects_cross_tenant_and_non_empty_delete(self) -> None:
        library = services.save_library({"name": "Tenant Docs"}, self.current_user)["item"]
        folder = services.save_folder(
            {"library_id": int(library["id"]), "name": "Reports"},
            self.current_user,
        )["item"]

        with self.assertRaises(Exception) as caught:
            services.delete_library(int(library["id"]), self.current_user)

        self.assertEqual(getattr(caught.exception, "status_code", None), 409)

        other_user = {
            "id": 11,
            "username": "other",
            "current_tenant": {"id": 8, "tenant_key": "tenant-b", "name": "Tenant B"},
            "tenant_id": 8,
        }
        with self.assertRaises(Exception) as folder_caught:
            services.list_workspace(
                current_user=other_user,
                library_id=int(library["id"]),
                folder_id=int(folder["id"]),
            )

        self.assertEqual(getattr(folder_caught.exception, "status_code", None), 404)

    def test_workspace_reports_recursive_folder_size(self) -> None:
        self.create_default_profile()
        library = services.save_library({"name": "Knowledge"}, self.current_user)["item"]
        parent = services.save_folder(
            {"library_id": int(library["id"]), "name": "Parent"},
            self.current_user,
        )["item"]
        child = services.save_folder(
            {"library_id": int(library["id"]), "parent_id": int(parent["id"]), "name": "Child"},
            self.current_user,
        )["item"]
        services.upload_file(
            current_user=self.current_user,
            filename="root.txt",
            content_type="text/plain",
            stream=io.BytesIO(b"root"),
            library_id=int(library["id"]),
            folder_id=int(parent["id"]),
            visibility="tenant",
            metadata={},
        )
        services.upload_file(
            current_user=self.current_user,
            filename="child.txt",
            content_type="text/plain",
            stream=io.BytesIO(b"child-file"),
            library_id=int(library["id"]),
            folder_id=int(child["id"]),
            visibility="tenant",
            metadata={},
        )

        root_workspace = services.list_workspace(current_user=self.current_user, library_id=int(library["id"]))
        parent_row = next(item for item in root_workspace["folders"] if item["id"] == int(parent["id"]))
        self.assertEqual(parent_row["size_bytes"], 14)
        self.assertEqual(parent_row["file_count"], 2)
        self.assertEqual(root_workspace["current_usage"]["used_bytes"], 14)

        parent_workspace = services.list_workspace(
            current_user=self.current_user,
            library_id=int(library["id"]),
            folder_id=int(parent["id"]),
        )
        child_row = next(item for item in parent_workspace["folders"] if item["id"] == int(child["id"]))
        self.assertEqual(child_row["size_bytes"], 10)
        self.assertEqual(child_row["file_count"], 1)
        self.assertEqual(parent_workspace["current_usage"]["used_bytes"], 14)

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
