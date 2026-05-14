from __future__ import annotations

import os
import time
from urllib.parse import unquote, urlparse

import pytest


pytestmark = pytest.mark.skipif(
    not os.environ.get("FG_AGENT_MYSQL_TEST_URL"),
    reason="FG_AGENT_MYSQL_TEST_URL is required for MySQL integration tests",
)


def test_all_init_tasks_run_against_mysql() -> None:
    import pymysql

    from api.module_registry import module_init_tasks
    from system.application.database import connect, table_exists

    base_url = os.environ["FG_AGENT_MYSQL_TEST_URL"].rstrip("/")
    parsed = urlparse(base_url)
    database_name = f"ops_admin_mysql_test_{int(time.time())}"
    admin_conn = pymysql.connect(
        host=parsed.hostname,
        port=parsed.port or 3306,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with admin_conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        database_url = f"{base_url}/{database_name}"
        with connect(database_url, readonly=False) as conn:
            tasks = module_init_tasks()
            for name in (
                "identity_access",
                "basic_data",
                "llm_runtime",
                "appearance",
                "cron",
                "file_management",
                "messaging",
                "ai_assets",
            ):
                tasks[name](conn)
            assert conn.backend == "mysql"
            assert conn.execute("SELECT 1 FROM tenants LIMIT 1").fetchone()
            assert table_exists(conn, "llm_providers")
            assert table_exists(conn, "file_objects")
    finally:
        with admin_conn.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{database_name}`")
        admin_conn.close()
