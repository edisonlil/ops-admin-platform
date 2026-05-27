from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class SoftDeleteUniqueMarkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "soft-delete-unique.db"
        self.env_patch = mock.patch.dict(
            os.environ,
            {
                "FG_AGENT_DATABASE_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-database.json"),
                "OPS_ADMIN_APPLICATION_CONFIG": str(Path(tempfile.gettempdir()) / "ops-admin-missing-application.json"),
                "FG_AGENT_DATABASE_URL": "",
                "SUPABASE_DB_URL": "",
                "DATABASE_URL": "",
                "FG_AGENT_DB_PATH": str(self.db_path),
            },
            clear=False,
        )
        self.env_patch.start()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def initialize(self, ensure_schema) -> None:  # type: ignore[no-untyped-def]
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def test_data_access_policy_can_be_deleted_recreated_and_deleted_again(self) -> None:
        from authorization.infrastructure.persistence.bootstrap import ensure_authorization_schema
        from authorization.infrastructure.persistence import repositories

        self.initialize(ensure_authorization_schema)

        first = repositories.save_data_access_policy(
            tenant_id=7,
            subject_type="user",
            subject_id=3,
            resource_key="file.object",
            action="read",
            scope="self",
            department_ids=[],
            priority=100,
            actor="tester",
            actor_id=1,
        )
        self.assertIsNotNone(repositories.delete_data_access_policy(tenant_id=7, policy_id=first.id))
        second = repositories.save_data_access_policy(
            tenant_id=7,
            subject_type="user",
            subject_id=3,
            resource_key="file.object",
            action="read",
            scope="department",
            department_ids=[9],
            priority=90,
            actor="tester",
            actor_id=1,
        )
        self.assertIsNotNone(repositories.delete_data_access_policy(tenant_id=7, policy_id=second.id))

    def test_authorization_descriptor_relation_table_fields_round_trip(self) -> None:
        from authorization.infrastructure.persistence.bootstrap import ensure_authorization_schema
        from authorization.infrastructure.persistence import repositories

        self.initialize(ensure_authorization_schema)

        item = repositories.upsert_resource_descriptor(
            {
                "resource_key": "demo.document",
                "name": "Demo Document",
                "access_mode": "relation_table",
                "resource_id_column": "id",
                "relation_table": "demo_document_members",
                "relation_resource_id_column": "document_id",
                "relation_user_column": "subject_user_id",
                "relation_department_column": "subject_department_id",
                "relation_tenant_column": "tenant_id",
                "relation_deleted_column": "deleted",
                "relation_resource_key_column": "resource_key",
                "relation_resource_key_value": "demo.document",
                "relation_subject_type_column": "subject_type",
                "relation_subject_type_user_value": "user",
                "relation_subject_type_department_value": "department",
                "supported_scopes": ["self", "department", "tenant"],
            },
            actor="tester",
            actor_id=1,
        )

        self.assertEqual(item.access_mode, "relation_table")
        self.assertEqual(item.resource_id_column, "id")
        self.assertEqual(item.relation_table, "demo_document_members")
        self.assertEqual(item.relation_resource_id_column, "document_id")
        self.assertEqual(item.relation_user_column, "subject_user_id")
        self.assertEqual(item.relation_department_column, "subject_department_id")
        self.assertEqual(item.relation_subject_type_user_value, "user")

    def test_authorization_init_adds_descriptor_relation_columns_and_seed_preserves_custom_config(self) -> None:
        from authorization.infrastructure.persistence.bootstrap import ensure_authorization_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute(
                """
                CREATE TABLE data_resource_descriptors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id INTEGER NOT NULL DEFAULT 1,
                    resource_key TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    tenant_column TEXT NOT NULL DEFAULT 'tenant_id',
                    creator_column TEXT NOT NULL DEFAULT 'creator_id',
                    owner_user_column TEXT NOT NULL DEFAULT 'owner_user_id',
                    owner_department_column TEXT NOT NULL DEFAULT 'owner_department_id',
                    supported_scopes_json TEXT NOT NULL DEFAULT '[]',
                    requires_data_scope INTEGER NOT NULL DEFAULT 0,
                    lock_version INTEGER NOT NULL DEFAULT 0,
                    deleted INTEGER NOT NULL DEFAULT 0,
                    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    creator TEXT DEFAULT NULL,
                    creator_id INTEGER DEFAULT NULL,
                    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    editor TEXT DEFAULT NULL,
                    editor_id INTEGER DEFAULT NULL,
                    UNIQUE (resource_key, deleted)
                )
                """
            )
            conn.execute(
                """
                INSERT INTO data_resource_descriptors (
                    resource_key, name, description, tenant_column, creator_column,
                    owner_user_column, owner_department_column, supported_scopes_json, requires_data_scope
                )
                VALUES ('basic-data.region', 'Region', 'custom', 'tenant_id', 'creator_id',
                        'owner_user_id', 'owner_department_id', '["self","tenant"]', 0)
                """
            )
            conn.execute(
                """
                CREATE TABLE data_access_policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id INTEGER NOT NULL DEFAULT 1,
                    subject_type TEXT NOT NULL,
                    subject_id INTEGER NOT NULL,
                    resource_key TEXT NOT NULL,
                    action TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    department_ids_json TEXT NOT NULL DEFAULT '[]',
                    priority INTEGER NOT NULL DEFAULT 100,
                    lock_version INTEGER NOT NULL DEFAULT 0,
                    deleted INTEGER NOT NULL DEFAULT 0,
                    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    creator TEXT DEFAULT NULL,
                    creator_id INTEGER DEFAULT NULL,
                    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    editor TEXT DEFAULT NULL,
                    editor_id INTEGER DEFAULT NULL,
                    UNIQUE (tenant_id, subject_type, subject_id, resource_key, action, deleted)
                )
                """
            )
            conn.commit()

            ensure_authorization_schema(conn)
            conn.execute(
                """
                UPDATE data_resource_descriptors
                SET access_mode = 'relation_table',
                    relation_table = 'region_members',
                    relation_resource_id_column = 'region_id',
                    relation_user_column = 'user_id'
                WHERE resource_key = 'basic-data.region'
                """
            )
            ensure_authorization_schema(conn)
            row = conn.execute(
                """
                SELECT access_mode, relation_table, relation_resource_id_column, relation_user_column
                FROM data_resource_descriptors
                WHERE resource_key = 'basic-data.region' AND deleted = 0
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(row["access_mode"], "relation_table")
        self.assertEqual(row["relation_table"], "region_members")
        self.assertEqual(row["relation_resource_id_column"], "region_id")
        self.assertEqual(row["relation_user_column"], "user_id")

    def test_authorization_require_schema_checks_descriptor_relation_columns(self) -> None:
        from authorization.infrastructure.persistence.bootstrap import require_authorization_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute(
                """
                CREATE TABLE data_resource_descriptors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id INTEGER NOT NULL DEFAULT 1,
                    resource_key TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    tenant_column TEXT NOT NULL DEFAULT 'tenant_id',
                    creator_column TEXT NOT NULL DEFAULT 'creator_id',
                    owner_user_column TEXT NOT NULL DEFAULT 'owner_user_id',
                    owner_department_column TEXT NOT NULL DEFAULT 'owner_department_id',
                    supported_scopes_json TEXT NOT NULL DEFAULT '[]',
                    requires_data_scope INTEGER NOT NULL DEFAULT 0,
                    lock_version INTEGER NOT NULL DEFAULT 0,
                    deleted INTEGER NOT NULL DEFAULT 0,
                    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    creator TEXT DEFAULT NULL,
                    creator_id INTEGER DEFAULT NULL,
                    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    editor TEXT DEFAULT NULL,
                    editor_id INTEGER DEFAULT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE data_access_policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id INTEGER NOT NULL DEFAULT 1,
                    subject_type TEXT NOT NULL,
                    subject_id INTEGER NOT NULL,
                    resource_key TEXT NOT NULL,
                    action TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    department_ids_json TEXT NOT NULL DEFAULT '[]',
                    priority INTEGER NOT NULL DEFAULT 100,
                    active_marker INTEGER DEFAULT 1,
                    lock_version INTEGER NOT NULL DEFAULT 0,
                    deleted INTEGER NOT NULL DEFAULT 0,
                    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    creator TEXT DEFAULT NULL,
                    creator_id INTEGER DEFAULT NULL,
                    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    editor TEXT DEFAULT NULL,
                    editor_id INTEGER DEFAULT NULL
                )
                """
            )
            conn.commit()
            with self.assertRaisesRegex(RuntimeError, "data_resource_descriptors.access_mode"):
                require_authorization_schema(conn)
        finally:
            conn.close()

    def test_authorization_resource_descriptor_dto_requires_relation_table_columns(self) -> None:
        from pydantic import ValidationError

        from authorization.interfaces.http.dtos import ResourceDescriptorRequest

        with self.assertRaises(ValidationError):
            ResourceDescriptorRequest(
                resource_key="demo.document",
                name="Demo Document",
                access_mode="relation_table",
                supported_scopes=["self"],
                relation_table="demo_document_members",
                relation_resource_id_column="document_id",
            )

        valid = ResourceDescriptorRequest(
            resource_key="demo.document",
            name="Demo Document",
            access_mode="relation_table",
            supported_scopes=["self"],
            relation_table="demo_document_members",
            relation_resource_id_column="document_id",
            relation_user_column="subject_user_id",
        )
        self.assertEqual(valid.access_mode, "relation_table")

    def test_file_library_and_folder_can_be_deleted_recreated_and_deleted_again(self) -> None:
        from file_management.infrastructure.persistence.bootstrap import ensure_file_management_schema
        from file_management.infrastructure.persistence import repositories

        self.initialize(ensure_file_management_schema)

        first_library = repositories.save_library(
            tenant_id=7,
            library_id=None,
            payload={"name": "Shared"},
            actor="tester",
            actor_id=1,
        )
        self.assertIsNotNone(first_library)
        self.assertTrue(repositories.delete_library(tenant_id=7, library_id=first_library.id, actor="tester", actor_id=1))
        second_library = repositories.save_library(
            tenant_id=7,
            library_id=None,
            payload={"name": "Shared"},
            actor="tester",
            actor_id=1,
        )
        self.assertIsNotNone(second_library)
        self.assertTrue(repositories.delete_library(tenant_id=7, library_id=second_library.id, actor="tester", actor_id=1))

        parent_library = repositories.save_library(
            tenant_id=7,
            library_id=None,
            payload={"name": "Folders"},
            actor="tester",
            actor_id=1,
        )
        self.assertIsNotNone(parent_library)
        first_folder = repositories.save_folder(
            tenant_id=7,
            folder_id=None,
            payload={"library_id": parent_library.id, "name": "Archive"},
            actor="tester",
            actor_id=1,
        )
        self.assertIsNotNone(first_folder)
        self.assertTrue(repositories.delete_folder(tenant_id=7, folder_id=first_folder.id, actor="tester", actor_id=1))
        second_folder = repositories.save_folder(
            tenant_id=7,
            folder_id=None,
            payload={"library_id": parent_library.id, "name": "Archive"},
            actor="tester",
            actor_id=1,
        )
        self.assertIsNotNone(second_folder)
        self.assertTrue(repositories.delete_folder(tenant_id=7, folder_id=second_folder.id, actor="tester", actor_id=1))

    def test_prompt_asset_can_be_deleted_recreated_and_deleted_again(self) -> None:
        from ai_assets.infrastructure.persistence.bootstrap import ensure_ai_assets_schema
        from ai_assets.infrastructure.persistence import repositories
        from ai_assets.domain.models import PROMPT_ASSET_STATUS_ARCHIVED

        self.initialize(ensure_ai_assets_schema)

        first = repositories.save_prompt_asset(
            tenant_id=7,
            prompt_id=None,
            payload={"prompt_key": "voice.summary", "name": "Voice Summary", "status": PROMPT_ASSET_STATUS_ARCHIVED},
            actor="tester",
            actor_id=1,
        )
        self.assertIsNotNone(first)
        self.assertTrue(repositories.delete_archived_prompt_asset(tenant_id=7, prompt_id=first.id, actor="tester", actor_id=1))
        second = repositories.save_prompt_asset(
            tenant_id=7,
            prompt_id=None,
            payload={"prompt_key": "voice.summary", "name": "Voice Summary", "status": PROMPT_ASSET_STATUS_ARCHIVED},
            actor="tester",
            actor_id=1,
        )
        self.assertIsNotNone(second)
        self.assertTrue(repositories.delete_archived_prompt_asset(tenant_id=7, prompt_id=second.id, actor="tester", actor_id=1))
