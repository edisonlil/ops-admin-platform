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


if __name__ == "__main__":
    unittest.main()
