from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_appearance_schema(conn: Any) -> None:
    filename = "ddl.postgres.sql" if getattr(conn, "backend", "sqlite") == "postgres" else "ddl.sqlite.sql"
    apply_sql_script(conn, PERSISTENCE_DIR / filename)
    ensure_draft_columns(conn)
    ensure_platform_branding_columns(conn)


def require_appearance_schema(conn: Any) -> None:
    required_tables = (
        "appearance_themes",
        "appearance_theme_assignments",
        "appearance_theme_revisions",
        "appearance_platform_branding",
    )
    missing = [table_name for table_name in required_tables if not table_exists(conn, table_name)]
    if missing:
        raise RuntimeError(
            "appearance storage is not initialized; run `python scripts/init_appearance.py`"
            + f" (missing tables: {', '.join(missing)})"
        )
    missing_columns = [
        column_name
        for column_name in (
            "draft_preset_id",
            "draft_token_overrides_json",
            "draft_layout_overrides_json",
            "project_overrides_json",
            "draft_project_overrides_json",
            "draft_skin_class",
        )
        if not has_column(conn, "appearance_themes", column_name)
    ]
    if missing_columns:
        raise RuntimeError(
            "appearance storage is not initialized; run `python scripts/init_appearance.py`"
            + f" (missing columns: {', '.join(missing_columns)})"
        )
    missing_branding_columns = [
        column_name
        for column_name in ("platform_name", "logo_url", "platform_name_font_size", "updated_by", "updated_at")
        if not has_column(conn, "appearance_platform_branding", column_name)
    ]
    if missing_branding_columns:
        raise RuntimeError(
            "appearance storage is not initialized; run `python scripts/init_appearance.py`"
            + f" (missing columns: {', '.join(missing_branding_columns)})"
        )


def ensure_draft_columns(conn: Any) -> None:
    default_columns = {
        "draft_preset_id": "TEXT NOT NULL DEFAULT 'default'",
        "draft_token_overrides_json": "JSONB NOT NULL DEFAULT '{}'::jsonb"
        if getattr(conn, "backend", "sqlite") == "postgres"
        else "TEXT NOT NULL DEFAULT '{}'",
        "draft_layout_overrides_json": "JSONB NOT NULL DEFAULT '{}'::jsonb"
        if getattr(conn, "backend", "sqlite") == "postgres"
        else "TEXT NOT NULL DEFAULT '{}'",
        "project_overrides_json": "JSONB NOT NULL DEFAULT '{}'::jsonb"
        if getattr(conn, "backend", "sqlite") == "postgres"
        else "TEXT NOT NULL DEFAULT '{}'",
        "draft_project_overrides_json": "JSONB NOT NULL DEFAULT '{}'::jsonb"
        if getattr(conn, "backend", "sqlite") == "postgres"
        else "TEXT NOT NULL DEFAULT '{}'",
        "draft_skin_class": "TEXT NOT NULL DEFAULT ''",
    }
    for column_name, definition in default_columns.items():
        if has_column(conn, "appearance_themes", column_name):
            continue
        if getattr(conn, "backend", "sqlite") == "postgres":
            conn.execute(f"ALTER TABLE appearance_themes ADD COLUMN IF NOT EXISTS {column_name} {definition}")
        else:
            conn.execute(f"ALTER TABLE appearance_themes ADD COLUMN {column_name} {definition}")
    conn.execute(
        """
        UPDATE appearance_themes
        SET draft_preset_id = CASE WHEN draft_preset_id IS NULL OR draft_preset_id = '' THEN preset_id ELSE draft_preset_id END,
            draft_token_overrides_json = CASE WHEN draft_token_overrides_json IS NULL OR draft_token_overrides_json = '' THEN token_overrides_json ELSE draft_token_overrides_json END,
            draft_layout_overrides_json = CASE WHEN draft_layout_overrides_json IS NULL OR draft_layout_overrides_json = '' THEN layout_overrides_json ELSE draft_layout_overrides_json END,
            project_overrides_json = CASE WHEN project_overrides_json IS NULL OR project_overrides_json = '' THEN '{}' ELSE project_overrides_json END,
            draft_project_overrides_json = CASE WHEN draft_project_overrides_json IS NULL OR draft_project_overrides_json = '' THEN project_overrides_json ELSE draft_project_overrides_json END,
            draft_skin_class = CASE WHEN draft_skin_class IS NULL THEN skin_class ELSE draft_skin_class END
        """
    )


def ensure_platform_branding_columns(conn: Any) -> None:
    if not table_exists(conn, "appearance_platform_branding"):
        return
    if has_column(conn, "appearance_platform_branding", "platform_name_font_size"):
        return
    definition = "BIGINT NOT NULL DEFAULT 20" if getattr(conn, "backend", "sqlite") == "postgres" else "INTEGER NOT NULL DEFAULT 20"
    if getattr(conn, "backend", "sqlite") == "postgres":
        conn.execute(f"ALTER TABLE appearance_platform_branding ADD COLUMN IF NOT EXISTS platform_name_font_size {definition}")
    else:
        conn.execute(f"ALTER TABLE appearance_platform_branding ADD COLUMN platform_name_font_size {definition}")


def apply_sql_script(conn: Any, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    if getattr(conn, "backend", "sqlite") != "postgres" and hasattr(conn, "executescript"):
        conn.executescript(sql)
        return
    for statement in split_sql_statements(sql):
        conn.execute(statement)


def split_sql_statements(sql: str) -> Iterable[str]:
    for chunk in sql.split(";"):
        statement = chunk.strip()
        if not statement:
            continue
        if all(not line.strip() or line.strip().startswith("--") for line in statement.splitlines()):
            continue
        yield statement


def table_exists(conn: Any, table_name: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "postgres":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ?
            """,
            (table_name,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
    return bool(row)


def has_column(conn: Any, table_name: str, column_name: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "postgres":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
            """,
            (table_name, column_name),
        ).fetchone()
        return bool(row)
    columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    return column_name in columns
