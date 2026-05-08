from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from appearance.domain.branding import DEFAULT_PLATFORM_NAME, PlatformBranding
from appearance.domain.theme import AppearancePayload, AppearanceTheme, THEME_STATUS_PUBLISHED
from appearance.infrastructure.persistence.bootstrap import require_appearance_schema
from system.application.database import connect, resolve_database_url, resolve_db_path


TENANT_SCOPE = "tenant"
PLATFORM_SCOPE = "platform"
THEME_STATUS_DRAFT = "draft"
THEME_STATUS_DISABLED = "disabled"


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def get_effective_tenant_theme(tenant_id: int) -> AppearanceTheme | None:
    source = "platform"
    with connect(database_target(), readonly=True) as conn:
        require_appearance_schema(conn)
        row = None
        if tenant_id > 0:
            row = conn.execute(
                """
                SELECT t.*
                FROM appearance_theme_assignments a
                JOIN appearance_themes t ON t.id = a.theme_id
                WHERE a.scope_type = ?
                  AND a.scope_id = ?
                  AND a.is_default = ?
                  AND t.status = ?
                ORDER BY a.assigned_at DESC, t.updated_at DESC, t.id DESC
                LIMIT 1
                """,
                (TENANT_SCOPE, tenant_id, True, THEME_STATUS_PUBLISHED),
            ).fetchone()
            if row:
                source = "tenant"
        if not row:
            row = conn.execute(
                """
                SELECT t.*
                FROM appearance_theme_assignments a
                JOIN appearance_themes t ON t.id = a.theme_id
                WHERE a.scope_type = ?
                  AND a.scope_id = ?
                  AND a.is_default = ?
                  AND t.status = ?
                ORDER BY a.assigned_at DESC, t.updated_at DESC, t.id DESC
                LIMIT 1
                """,
                (PLATFORM_SCOPE, 0, True, THEME_STATUS_PUBLISHED),
            ).fetchone()
    if not row:
        return None
    theme = row_to_theme(dict(row))
    data = theme.to_dict()
    data["effective_source"] = source
    return theme_with_extra(theme, data)


def list_themes() -> list[AppearanceTheme]:
    with connect(database_target(), readonly=True) as conn:
        require_appearance_schema(conn)
        rows = conn.execute(
            """
            SELECT
                t.*,
                (
                    SELECT COUNT(*)
                    FROM appearance_theme_assignments a
                    WHERE a.theme_id = t.id
                      AND a.scope_type = 'tenant'
                      AND a.is_default = 1
                ) AS tenant_assignment_count
                ,
                (
                    SELECT COUNT(*)
                    FROM appearance_theme_assignments a
                    WHERE a.theme_id = t.id
                      AND a.scope_type = 'platform'
                      AND a.scope_id = 0
                      AND a.is_default = 1
                ) AS platform_default_count
            FROM appearance_themes t
            ORDER BY
                CASE t.status
                    WHEN 'draft' THEN 0
                    WHEN 'published' THEN 1
                    ELSE 2
                END,
                t.updated_at DESC,
                t.id DESC
            """
        ).fetchall()
    themes = []
    for row in rows:
        theme = row_to_theme(dict(row))
        data = theme.to_dict()
        row_data = dict(row)
        data["tenant_assignment_count"] = int(row_data.get("tenant_assignment_count", 0) or 0)
        data["is_platform_default"] = (
            theme.status == THEME_STATUS_PUBLISHED and int(row_data.get("platform_default_count", 0) or 0) > 0
        )
        themes.append(theme_with_extra(theme, data))
    return themes


def get_platform_branding() -> PlatformBranding:
    with connect(database_target(), readonly=True) as conn:
        require_appearance_schema(conn)
        row = conn.execute(
            """
            SELECT platform_name, logo_url, platform_name_font_size, updated_by, updated_at
            FROM appearance_platform_branding
            WHERE id = ?
            """,
            (1,),
        ).fetchone()
    if not row:
        return PlatformBranding.from_values(platform_name=DEFAULT_PLATFORM_NAME, logo_url="")
    return row_to_platform_branding(dict(row))


def save_platform_branding(
    *,
    platform_name: str,
    logo_url: str,
    platform_name_font_size: int,
    actor: str,
) -> PlatformBranding:
    timestamp = now_iso()
    branding = PlatformBranding.from_values(
        platform_name=platform_name,
        logo_url=logo_url,
        platform_name_font_size=platform_name_font_size,
        updated_by=actor,
        updated_at=timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_appearance_schema(conn)
        existing = conn.execute("SELECT id FROM appearance_platform_branding WHERE id = ?", (1,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE appearance_platform_branding
                SET platform_name = ?,
                    logo_url = ?,
                    platform_name_font_size = ?,
                    updated_by = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (branding.platform_name, branding.logo_url, branding.platform_name_font_size, actor, timestamp, 1),
            )
        else:
            conn.execute(
                """
                INSERT INTO appearance_platform_branding (
                    id, platform_name, logo_url, platform_name_font_size, updated_by, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (1, branding.platform_name, branding.logo_url, branding.platform_name_font_size, actor, timestamp),
            )
        row = conn.execute(
            """
            SELECT platform_name, logo_url, platform_name_font_size, updated_by, updated_at
            FROM appearance_platform_branding
            WHERE id = ?
            """,
            (1,),
        ).fetchone()
    return row_to_platform_branding(dict(row))


def get_theme(theme_id: int) -> AppearanceTheme | None:
    with connect(database_target(), readonly=True) as conn:
        require_appearance_schema(conn)
        row = conn.execute("SELECT * FROM appearance_themes WHERE id = ?", (theme_id,)).fetchone()
    return row_to_theme(dict(row)) if row else None


def create_theme(*, name: str, payload: AppearancePayload, actor: str) -> AppearanceTheme:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_appearance_schema(conn)
        cursor = conn.execute(
            """
            INSERT INTO appearance_themes (
                tenant_id, name, status, version, preset_id, token_overrides_json,
                layout_overrides_json, project_overrides_json, skin_class, draft_preset_id,
                draft_token_overrides_json, draft_layout_overrides_json, draft_project_overrides_json,
                draft_skin_class, created_by, updated_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                0,
                name,
                THEME_STATUS_DRAFT,
                1,
                "default",
                "{}",
                "{}",
                "{}",
                "",
                payload.preset_id,
                encode_json(payload.token_overrides),
                encode_json(payload.layout_overrides),
                encode_json(payload.project_overrides),
                payload.skin_class,
                actor,
                actor,
                timestamp,
                timestamp,
            ),
        )
        theme_id = int(getattr(cursor, "lastrowid", 0) or 0)
        if not theme_id:
            row = conn.execute(
                """
                SELECT id
                FROM appearance_themes
                WHERE created_at = ? AND created_by = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (timestamp, actor),
            ).fetchone()
            theme_id = int(row["id"])
        row = conn.execute("SELECT * FROM appearance_themes WHERE id = ?", (theme_id,)).fetchone()
    return row_to_theme(dict(row))


def update_theme(*, theme_id: int, name: str, payload: AppearancePayload, actor: str) -> AppearanceTheme | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_appearance_schema(conn)
        existing = conn.execute("SELECT * FROM appearance_themes WHERE id = ?", (theme_id,)).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE appearance_themes
            SET name = ?,
                draft_preset_id = ?,
                draft_token_overrides_json = ?,
                draft_layout_overrides_json = ?,
                draft_project_overrides_json = ?,
                draft_skin_class = ?,
                updated_by = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                name,
                payload.preset_id,
                encode_json(payload.token_overrides),
                encode_json(payload.layout_overrides),
                encode_json(payload.project_overrides),
                payload.skin_class,
                actor,
                timestamp,
                theme_id,
            ),
        )
        row = conn.execute("SELECT * FROM appearance_themes WHERE id = ?", (theme_id,)).fetchone()
    return row_to_theme(dict(row))


def publish_theme(*, theme_id: int, actor: str) -> AppearanceTheme | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_appearance_schema(conn)
        existing = conn.execute("SELECT * FROM appearance_themes WHERE id = ?", (theme_id,)).fetchone()
        if not existing:
            return None
        next_version = int(existing["version"] or 1)
        if str(existing["status"] or "") != THEME_STATUS_PUBLISHED:
            next_version += 1
        conn.execute(
            """
            UPDATE appearance_themes
            SET status = ?,
                version = ?,
                preset_id = draft_preset_id,
                token_overrides_json = draft_token_overrides_json,
                layout_overrides_json = draft_layout_overrides_json,
                project_overrides_json = draft_project_overrides_json,
                skin_class = draft_skin_class,
                updated_by = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (THEME_STATUS_PUBLISHED, next_version, actor, timestamp, theme_id),
        )
        row = conn.execute("SELECT * FROM appearance_themes WHERE id = ?", (theme_id,)).fetchone()
        snapshot = dict(row_to_theme(dict(row)).to_dict())
        conn.execute(
            """
            INSERT INTO appearance_theme_revisions (
                theme_id, revision_no, snapshot_json, created_by, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (theme_id, revision_number(conn, theme_id), encode_json(snapshot), actor, timestamp),
        )
    return row_to_theme(dict(row))


def disable_theme(*, theme_id: int, actor: str) -> AppearanceTheme | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_appearance_schema(conn)
        existing = conn.execute("SELECT * FROM appearance_themes WHERE id = ?", (theme_id,)).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE appearance_themes
            SET status = ?,
                updated_by = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (THEME_STATUS_DISABLED, actor, timestamp, theme_id),
        )
        conn.execute(
            """
            DELETE FROM appearance_theme_assignments
            WHERE scope_type = ? AND scope_id = ? AND is_default = ? AND theme_id = ?
            """,
            (PLATFORM_SCOPE, 0, True, theme_id),
        )
        row = conn.execute("SELECT * FROM appearance_themes WHERE id = ?", (theme_id,)).fetchone()
    return row_to_theme(dict(row))


def assign_theme_to_tenant(*, tenant_id: int, theme_id: int | None, actor: str) -> AppearanceTheme | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_appearance_schema(conn)
        conn.execute(
            """
            DELETE FROM appearance_theme_assignments
            WHERE scope_type = ? AND scope_id = ? AND is_default = ?
            """,
            (TENANT_SCOPE, tenant_id, True),
        )
        if theme_id is None:
            return None
        theme = conn.execute(
            "SELECT * FROM appearance_themes WHERE id = ? AND status = ?",
            (theme_id, THEME_STATUS_PUBLISHED),
        ).fetchone()
        if not theme:
            return None
        conn.execute(
            """
            INSERT INTO appearance_theme_assignments (
                scope_type, scope_id, theme_id, is_default, assigned_by, assigned_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (TENANT_SCOPE, tenant_id, theme_id, True, actor, timestamp),
        )
    return get_theme(theme_id)


def assign_platform_default_theme(*, theme_id: int, actor: str) -> AppearanceTheme | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_appearance_schema(conn)
        theme = conn.execute(
            "SELECT * FROM appearance_themes WHERE id = ? AND status = ?",
            (theme_id, THEME_STATUS_PUBLISHED),
        ).fetchone()
        if not theme:
            return None
        conn.execute(
            """
            DELETE FROM appearance_theme_assignments
            WHERE scope_type = ? AND scope_id = ? AND is_default = ?
            """,
            (PLATFORM_SCOPE, 0, True),
        )
        conn.execute(
            """
            INSERT INTO appearance_theme_assignments (
                scope_type, scope_id, theme_id, is_default, assigned_by, assigned_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (PLATFORM_SCOPE, 0, theme_id, True, actor, timestamp),
        )
    return get_theme(theme_id)


def get_tenant_assigned_theme(tenant_id: int) -> AppearanceTheme | None:
    with connect(database_target(), readonly=True) as conn:
        require_appearance_schema(conn)
        row = conn.execute(
            """
            SELECT t.*
            FROM appearance_theme_assignments a
            JOIN appearance_themes t ON t.id = a.theme_id
            WHERE a.scope_type = ?
              AND a.scope_id = ?
              AND a.is_default = ?
            ORDER BY a.assigned_at DESC, t.updated_at DESC, t.id DESC
            LIMIT 1
            """,
            (TENANT_SCOPE, tenant_id, True),
        ).fetchone()
    return row_to_theme(dict(row)) if row else None


def save_published_tenant_theme(
    *,
    tenant_id: int,
    name: str,
    payload: AppearancePayload,
    actor: str,
) -> AppearanceTheme:
    theme = create_theme(name=name, payload=payload, actor=actor)
    theme = publish_theme(theme_id=theme.id, actor=actor) or theme
    assign_theme_to_tenant(tenant_id=tenant_id, theme_id=theme.id, actor=actor)
    return theme


def revision_number(conn: Any, theme_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(revision_no), 0) + 1 AS next_revision FROM appearance_theme_revisions WHERE theme_id = ?",
        (theme_id,),
    ).fetchone()
    return int(row["next_revision"] if row else 1)


def row_to_theme(row: dict[str, Any]) -> AppearanceTheme:
    return AppearanceTheme(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        name=str(row.get("name", "")),
        status=str(row.get("status", THEME_STATUS_PUBLISHED) or THEME_STATUS_PUBLISHED),
        version=int(row.get("version", 1) or 1),
        payload=AppearancePayload(
            version=1,
            preset_id=str(row.get("preset_id", "") or "default"),
            token_overrides=decode_json(row.get("token_overrides_json")),
            layout_overrides=decode_json(row.get("layout_overrides_json")),
            project_overrides=decode_json(row.get("project_overrides_json")),
            skin_class=str(row.get("skin_class", "") or ""),
        ),
        draft_payload=AppearancePayload(
            version=1,
            preset_id=str(row.get("draft_preset_id", "") or row.get("preset_id", "") or "default"),
            token_overrides=decode_json(row.get("draft_token_overrides_json", row.get("token_overrides_json"))),
            layout_overrides=decode_json(row.get("draft_layout_overrides_json", row.get("layout_overrides_json"))),
            project_overrides=decode_json(row.get("draft_project_overrides_json", row.get("project_overrides_json"))),
            skin_class=str(row.get("draft_skin_class", row.get("skin_class", "")) or ""),
        ),
        created_by=str(row.get("created_by", "") or ""),
        updated_by=str(row.get("updated_by", "") or ""),
        created_at=str(row.get("created_at", "") or ""),
        updated_at=str(row.get("updated_at", "") or ""),
    )


def row_to_platform_branding(row: dict[str, Any]) -> PlatformBranding:
    return PlatformBranding.from_values(
        platform_name=str(row.get("platform_name", DEFAULT_PLATFORM_NAME) or DEFAULT_PLATFORM_NAME),
        logo_url=str(row.get("logo_url", "") or ""),
        platform_name_font_size=row.get("platform_name_font_size", 20),
        updated_by=str(row.get("updated_by", "") or ""),
        updated_at=str(row.get("updated_at", "") or ""),
    )


def theme_with_extra(theme: AppearanceTheme, data: dict[str, Any]) -> AppearanceTheme:
    class ThemeView(AppearanceTheme):
        def to_dict(self) -> dict[str, Any]:
            return data

    return ThemeView(
        id=theme.id,
        tenant_id=theme.tenant_id,
        name=theme.name,
        status=theme.status,
        version=theme.version,
        payload=theme.payload,
        draft_payload=theme.draft_payload,
        created_by=theme.created_by,
        updated_by=theme.updated_by,
        created_at=theme.created_at,
        updated_at=theme.updated_at,
    )


def encode_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def decode_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
