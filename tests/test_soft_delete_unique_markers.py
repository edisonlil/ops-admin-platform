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
