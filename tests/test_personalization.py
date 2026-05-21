from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class PersonalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "ops-admin-personalization-test.db"
        self.env_patch = mock.patch.dict(
            "os.environ",
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
        self.initialize_personalization_db()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def initialize_personalization_db(self) -> None:
        from personalization.infrastructure.persistence.bootstrap import ensure_personalization_schema

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_personalization_schema(conn)
            conn.commit()
        finally:
            conn.close()

    def test_table_column_preference_can_be_saved_replaced_and_reset(self) -> None:
        from personalization.infrastructure.persistence import repositories

        saved = repositories.save_table_column_preference(
            tenant_id=1,
            user_id=7,
            view_key="rbac.user:table",
            visible_column_keys=["username", "status"],
            column_order_keys=["status", "username", "actions"],
            settings={"density": "compact"},
            actor="admin",
            actor_id=7,
        )
        self.assertEqual(saved.visible_column_keys, ["username", "status"])
        self.assertEqual(saved.column_order_keys, ["status", "username", "actions"])
        self.assertEqual(saved.settings, {"density": "compact"})

        replaced = repositories.save_table_column_preference(
            tenant_id=1,
            user_id=7,
            view_key="rbac.user:table",
            visible_column_keys=["username", "actions"],
            column_order_keys=["username", "actions"],
            settings={},
            actor="admin",
            actor_id=7,
        )
        self.assertEqual(replaced.id, saved.id)
        self.assertEqual(replaced.visible_column_keys, ["username", "actions"])
        self.assertEqual(replaced.settings, {})

        repositories.delete_table_column_preference(
            tenant_id=1,
            user_id=7,
            view_key="rbac.user:table",
            actor="admin",
            actor_id=7,
        )
        self.assertIsNone(
            repositories.get_table_column_preference(tenant_id=1, user_id=7, view_key="rbac.user:table")
        )

    def test_table_column_preference_persists_column_width_settings(self) -> None:
        from personalization.infrastructure.persistence import repositories

        saved = repositories.save_table_column_preference(
            tenant_id=2,
            user_id=9,
            view_key="projects:table:id",
            visible_column_keys=["ticket_no", "project_name"],
            column_order_keys=["ticket_no", "project_name"],
            settings={"column_widths": {"ticket_no": 72, "project_name": 388}},
            actor="admin",
            actor_id=9,
        )

        self.assertEqual(saved.settings["column_widths"], {"ticket_no": 72, "project_name": 388})

        loaded = repositories.get_table_column_preference(
            tenant_id=2,
            user_id=9,
            view_key="projects:table:id",
        )

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.settings["column_widths"], {"ticket_no": 72, "project_name": 388})

    def test_table_column_preference_recovers_from_concurrent_insert_duplicate(self) -> None:
        from personalization.infrastructure.persistence import repositories

        repositories.save_table_column_preference(
            tenant_id=3,
            user_id=11,
            view_key="organization.departments:table:default",
            visible_column_keys=["name"],
            column_order_keys=["name"],
            settings={"column_widths": {"name": 180}},
            actor="admin",
            actor_id=11,
        )

        original_insert = repositories.insert_table_column_preference
        original_update = repositories.update_table_column_preference
        raised_duplicate = False
        update_calls = 0

        def raise_duplicate_once(*args, **kwargs):
            nonlocal raised_duplicate
            if not raised_duplicate:
                raised_duplicate = True
                raise sqlite3.IntegrityError("UNIQUE constraint failed: personalization_table_column_preferences")
            return original_insert(*args, **kwargs)

        def miss_then_update(*args, **kwargs):
            nonlocal update_calls
            update_calls += 1
            if update_calls == 1:
                return False
            return original_update(*args, **kwargs)

        with (
            mock.patch.object(repositories, "update_table_column_preference", side_effect=miss_then_update),
            mock.patch.object(repositories, "insert_table_column_preference", side_effect=raise_duplicate_once),
        ):
            saved = repositories.save_table_column_preference(
                tenant_id=3,
                user_id=11,
                view_key="organization.departments:table:default",
                visible_column_keys=["name", "code"],
                column_order_keys=["code", "name"],
                settings={"column_widths": {"name": 96, "code": 84}},
                actor="admin",
                actor_id=11,
            )

        self.assertTrue(raised_duplicate)
        self.assertEqual(saved.visible_column_keys, ["name", "code"])
        self.assertEqual(saved.column_order_keys, ["code", "name"])
        self.assertEqual(saved.settings["column_widths"], {"name": 96, "code": 84})


if __name__ == "__main__":
    unittest.main()
