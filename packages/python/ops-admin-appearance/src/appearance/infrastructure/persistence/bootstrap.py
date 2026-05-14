from __future__ import annotations

from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import (
    add_column_if_missing,
    apply_sql_script,
    backend_name,
    bigint_type,
    column_exists as has_column,
    ddl_filename,
    table_exists,
    text_json_type,
)


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_appearance_schema(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))
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
        for column_name in ("platform_name", "logo_url", "platform_name_font_size", "editor", "update_time")
        if not has_column(conn, "appearance_platform_branding", column_name)
    ]
    if missing_branding_columns:
        raise RuntimeError(
            "appearance storage is not initialized; run `python scripts/init_appearance.py`"
            + f" (missing columns: {', '.join(missing_branding_columns)})"
        )


def ensure_draft_columns(conn: Any) -> None:
    json_default = "'{}'::jsonb" if backend_name(conn) == "postgres" else "'{}'"
    default_columns = {
        "draft_preset_id": "TEXT NOT NULL DEFAULT 'default'",
        "draft_token_overrides_json": f"{text_json_type(conn)} NOT NULL DEFAULT {json_default}",
        "draft_layout_overrides_json": f"{text_json_type(conn)} NOT NULL DEFAULT {json_default}",
        "project_overrides_json": f"{text_json_type(conn)} NOT NULL DEFAULT {json_default}",
        "draft_project_overrides_json": f"{text_json_type(conn)} NOT NULL DEFAULT {json_default}",
        "draft_skin_class": "TEXT NOT NULL DEFAULT ''",
    }
    for column_name, definition in default_columns.items():
        add_column_if_missing(conn, "appearance_themes", column_name, definition)
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
    add_column_if_missing(
        conn,
        "appearance_platform_branding",
        "platform_name_font_size",
        f"{bigint_type(conn)} NOT NULL DEFAULT 20",
    )
