from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_assets.domain.models import (
    PROMPT_ASSET_STATUS_ARCHIVED,
    PROMPT_ASSET_STATUS_DRAFT,
    PROMPT_ASSET_STATUS_PUBLISHED,
    PROMPT_VERSION_STATUS_DEPRECATED,
    PROMPT_VERSION_STATUS_PUBLISHED,
    PromptAsset,
    PromptVersion,
)
from ai_assets.infrastructure.persistence.bootstrap import require_ai_assets_schema
from system.application.data_access import DataAccessPredicate, ResourceDescriptor, apply_data_access
from system.application.database import connect, resolve_database_url, resolve_db_path
from system.application.sorting import build_order_by, parse_sort_params


PROMPT_ASSET_SORT_COLUMNS = {
    "id": "pa.id",
    "prompt_key": "pa.prompt_key",
    "name": "pa.name",
    "status": "effective_status",
    "version_count": "version_count",
    "create_time": "pa.create_time",
    "update_time": "pa.update_time",
}


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def published_version_exists_sql() -> str:
    return """
        SELECT 1
        FROM prompt_versions pv
        WHERE pv.prompt_id = pa.id AND pv.tenant_id = pa.tenant_id
            AND pv.status = 'published' AND pv.deleted = 0
    """


def effective_prompt_asset_status_sql() -> str:
    return f"""
        CASE
            WHEN pa.status = 'archived' THEN 'archived'
            WHEN EXISTS ({published_version_exists_sql()}) THEN 'published'
            ELSE 'draft'
        END
    """


PROMPT_ASSET_RESOURCE = ResourceDescriptor(resource_key="prompt.asset")


def list_prompt_assets(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    keyword: str = "",
    status: str = "",
    data_scope: DataAccessPredicate | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> tuple[list[PromptAsset], int]:
    start = (page - 1) * page_size
    filters = ["pa.tenant_id = ?", "pa.deleted = 0"]
    params: list[Any] = [tenant_id]
    apply_data_access(filters, params, data_scope=data_scope, resource=PROMPT_ASSET_RESOURCE, alias="pa")
    if keyword:
        filters.append("(pa.prompt_key LIKE ? OR pa.name LIKE ? OR pa.description LIKE ? OR pa.tags_json LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like, like, like])
    if status == PROMPT_ASSET_STATUS_PUBLISHED:
        filters.append(f"pa.status <> ? AND EXISTS ({published_version_exists_sql()})")
        params.append(PROMPT_ASSET_STATUS_ARCHIVED)
    elif status == PROMPT_ASSET_STATUS_DRAFT:
        filters.append(f"pa.status <> ? AND NOT EXISTS ({published_version_exists_sql()})")
        params.append(PROMPT_ASSET_STATUS_ARCHIVED)
    elif status:
        filters.append("pa.status = ?")
        params.append(status)
    where_sql = " AND ".join(filters)
    order_by = build_order_by(
        parse_sort_params(sort_by, sort_dir),
        allowed=PROMPT_ASSET_SORT_COLUMNS,
        default="pa.update_time DESC, pa.id DESC",
        tie_breaker="pa.id DESC",
    )
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM prompt_assets pa WHERE {where_sql}", tuple(params)))
        rows = conn.execute(
            f"""
            SELECT pa.*,
                   (SELECT COUNT(*) FROM prompt_versions pv
                    WHERE pv.prompt_id = pa.id AND pv.tenant_id = pa.tenant_id AND pv.deleted = 0) AS version_count,
                   {effective_prompt_asset_status_sql()} AS effective_status
            FROM prompt_assets pa
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, start),
        ).fetchall()
    return [row_to_asset(dict(row)) for row in rows], total


def get_prompt_asset(*, tenant_id: int, prompt_id: int, data_scope: DataAccessPredicate | None = None) -> PromptAsset | None:
    filters = ["pa.id = ?", "pa.tenant_id = ?", "pa.deleted = 0"]
    params: list[Any] = [prompt_id, tenant_id]
    apply_data_access(filters, params, data_scope=data_scope, resource=PROMPT_ASSET_RESOURCE, alias="pa")
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            f"""
            SELECT pa.*,
                   (SELECT COUNT(*) FROM prompt_versions pv
                    WHERE pv.prompt_id = pa.id AND pv.tenant_id = pa.tenant_id AND pv.deleted = 0) AS version_count,
                   {effective_prompt_asset_status_sql()} AS effective_status
            FROM prompt_assets pa
            WHERE {" AND ".join(filters)}
            """,
            tuple(params),
        ).fetchone()
    return row_to_asset(dict(row)) if row else None


def get_prompt_asset_by_key(*, tenant_id: int, prompt_key: str) -> PromptAsset | None:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            f"""
            SELECT pa.*,
                   (SELECT COUNT(*) FROM prompt_versions pv
                    WHERE pv.prompt_id = pa.id AND pv.tenant_id = pa.tenant_id AND pv.deleted = 0) AS version_count,
                   {effective_prompt_asset_status_sql()} AS effective_status
            FROM prompt_assets pa
            WHERE pa.prompt_key = ? AND pa.tenant_id = ? AND pa.deleted = 0
            """,
            (prompt_key, tenant_id),
        ).fetchone()
    return row_to_asset(dict(row)) if row else None


def prompt_key_exists(*, tenant_id: int, prompt_key: str) -> bool:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            """
            SELECT 1
            FROM prompt_assets
            WHERE tenant_id = ? AND prompt_key = ? AND deleted = 0
            LIMIT 1
            """,
            (tenant_id, prompt_key),
        ).fetchone()
    return bool(row)


def prompt_name_exists(*, tenant_id: int, name: str, exclude_prompt_id: int | None = None) -> bool:
    filters = ["tenant_id = ?", "name = ?", "deleted = 0"]
    params: list[Any] = [tenant_id, name]
    if exclude_prompt_id:
        filters.append("id <> ?")
        params.append(exclude_prompt_id)
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            f"""
            SELECT 1
            FROM prompt_assets
            WHERE {" AND ".join(filters)}
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()
    return bool(row)


def save_prompt_asset(
    *, tenant_id: int, prompt_id: int | None, payload: dict[str, Any], actor: str, actor_id: int | None
) -> PromptAsset | None:
    timestamp = now_iso()
    values = (
        str(payload["prompt_key"]),
        str(payload["name"]),
        str(payload.get("description") or ""),
        encode_json_list(payload.get("tags") if isinstance(payload.get("tags"), list) else []),
        str(payload.get("status") or "draft"),
        payload.get("owner_user_id"),
        payload.get("owner_department_id"),
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_ai_assets_schema(conn)
        if prompt_id:
            conn.execute(
                """
                UPDATE prompt_assets
                SET prompt_key = ?, name = ?, description = ?, tags_json = ?,
                    status = ?, owner_user_id = ?, owner_department_id = ?, editor = ?, editor_id = ?,
                    update_time = ?, lock_version = lock_version + 1
                WHERE id = ? AND tenant_id = ? AND deleted = 0
                """,
                (*values, prompt_id, tenant_id),
            )
            saved_id = prompt_id
        else:
            cursor = conn.execute(
                """
                INSERT INTO prompt_assets (
                    tenant_id, prompt_key, name, description, tags_json,
                    status, owner_user_id, owner_department_id, creator, creator_id,
                    editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, *values[:7], actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            saved_id = inserted_id(conn, cursor, "prompt_assets", timestamp, actor)
    return get_prompt_asset(tenant_id=tenant_id, prompt_id=saved_id)


def copy_prompt_asset(
    *,
    tenant_id: int,
    source_prompt_id: int,
    prompt_key: str,
    name: str,
    actor: str,
    actor_id: int | None,
) -> PromptAsset | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_ai_assets_schema(conn)
        source = conn.execute(
            """
            SELECT *
            FROM prompt_assets
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (source_prompt_id, tenant_id),
        ).fetchone()
        if not source:
            return None
        cursor = conn.execute(
            """
                INSERT INTO prompt_assets (
                    tenant_id, prompt_key, name, description, tags_json,
                    status, owner_user_id, owner_department_id, creator, creator_id,
                    editor, editor_id, create_time, update_time
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                prompt_key,
                name,
                str(source["description"] or ""),
                str(source["tags_json"] or "[]"),
                PROMPT_ASSET_STATUS_DRAFT,
                actor_id,
                source["owner_department_id"] if "owner_department_id" in source.keys() else None,
                actor,
                actor_id,
                actor,
                actor_id,
                timestamp,
                timestamp,
            ),
        )
        saved_id = inserted_id(conn, cursor, "prompt_assets", timestamp, actor)
        version_rows = conn.execute(
            """
            SELECT *
            FROM prompt_versions
            WHERE tenant_id = ? AND prompt_id = ? AND deleted = 0
            ORDER BY create_time ASC, id ASC
            """,
            (tenant_id, source_prompt_id),
        ).fetchall()
        for row in version_rows:
            conn.execute(
                """
                INSERT INTO prompt_versions (
                    tenant_id, prompt_id, version, system_prompt, developer_prompt,
                    user_prompt_template, variables_schema_json, output_schema_json,
                    example_inputs_json, example_outputs_json, model_preferences_json,
                    render_engine, status, creator, creator_id, editor, editor_id,
                    create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    saved_id,
                    str(row["version"] or ""),
                    str(row["system_prompt"] or ""),
                    str(row["developer_prompt"] or ""),
                    str(row["user_prompt_template"] or ""),
                    str(row["variables_schema_json"] or "{}"),
                    str(row["output_schema_json"] or "{}"),
                    str(row["example_inputs_json"] or "[]"),
                    str(row["example_outputs_json"] or "[]"),
                    str(row["model_preferences_json"] or "{}"),
                    str(row["render_engine"] or "simple"),
                    "draft",
                    actor,
                    actor_id,
                    actor,
                    actor_id,
                    timestamp,
                    timestamp,
                ),
            )
    return get_prompt_asset(tenant_id=tenant_id, prompt_id=saved_id)


def archive_prompt_asset(*, tenant_id: int, prompt_id: int, actor: str, actor_id: int | None) -> bool:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_ai_assets_schema(conn)
        cursor = conn.execute(
            """
            UPDATE prompt_assets
            SET status = ?, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (PROMPT_ASSET_STATUS_ARCHIVED, actor, actor_id, timestamp, prompt_id, tenant_id),
        )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def delete_archived_prompt_asset(*, tenant_id: int, prompt_id: int, actor: str, actor_id: int | None) -> bool:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_ai_assets_schema(conn)
        cursor = conn.execute(
            """
            UPDATE prompt_assets
            SET deleted = 1, active_marker = NULL, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND status = ? AND deleted = 0
            """,
            (actor, actor_id, timestamp, prompt_id, tenant_id, PROMPT_ASSET_STATUS_ARCHIVED),
        )
        if int(getattr(cursor, "rowcount", 0) or 0) > 0:
            conn.execute(
                """
                UPDATE prompt_versions
                SET deleted = 1, active_marker = NULL, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
                WHERE prompt_id = ? AND tenant_id = ? AND deleted = 0
                """,
                (actor, actor_id, timestamp, prompt_id, tenant_id),
            )
            return True
    return False


def list_prompt_versions(*, tenant_id: int, prompt_id: int) -> list[PromptVersion]:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        rows = conn.execute(
            """
            SELECT *
            FROM prompt_versions
            WHERE tenant_id = ? AND prompt_id = ? AND deleted = 0
            ORDER BY create_time DESC, id DESC
            """,
            (tenant_id, prompt_id),
        ).fetchall()
    return [row_to_version(dict(row)) for row in rows]


def get_prompt_version(*, tenant_id: int, version_id: int) -> PromptVersion | None:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            "SELECT * FROM prompt_versions WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (version_id, tenant_id),
        ).fetchone()
    return row_to_version(dict(row)) if row else None


def get_published_prompt_version(*, tenant_id: int, prompt_id: int) -> PromptVersion | None:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            """
            SELECT *
            FROM prompt_versions
            WHERE tenant_id = ? AND prompt_id = ? AND status = ? AND deleted = 0
            ORDER BY published_time DESC, update_time DESC, id DESC
            LIMIT 1
            """,
            (tenant_id, prompt_id, PROMPT_VERSION_STATUS_PUBLISHED),
        ).fetchone()
    return row_to_version(dict(row)) if row else None


def count_prompt_versions_by_status(*, tenant_id: int, prompt_id: int, status: str) -> int:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        return count_row(conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM prompt_versions
            WHERE tenant_id = ? AND prompt_id = ? AND status = ? AND deleted = 0
            """,
            (tenant_id, prompt_id, status),
        ))


def save_prompt_version(
    *, tenant_id: int, prompt_id: int, version_id: int | None, payload: dict[str, Any], actor: str, actor_id: int | None
) -> PromptVersion | None:
    timestamp = now_iso()
    values = (
        str(payload["version"]),
        str(payload.get("system_prompt") or ""),
        str(payload.get("developer_prompt") or ""),
        str(payload.get("user_prompt_template") or ""),
        encode_json_dict(payload.get("variables_schema")),
        encode_json_dict(payload.get("output_schema")),
        encode_json_list_of_dict(payload.get("example_inputs")),
        encode_json_list_of_dict(payload.get("example_outputs")),
        encode_json_dict(payload.get("model_preferences")),
        str(payload.get("render_engine") or "simple"),
        str(payload.get("status") or "draft"),
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_ai_assets_schema(conn)
        if version_id:
            conn.execute(
                """
                UPDATE prompt_versions
                SET version = ?, system_prompt = ?, developer_prompt = ?, user_prompt_template = ?,
                    variables_schema_json = ?, output_schema_json = ?, example_inputs_json = ?,
                    example_outputs_json = ?, model_preferences_json = ?, render_engine = ?, status = ?,
                    editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
                WHERE id = ? AND tenant_id = ? AND prompt_id = ? AND deleted = 0
                """,
                (*values, version_id, tenant_id, prompt_id),
            )
            saved_id = version_id
        else:
            cursor = conn.execute(
                """
                INSERT INTO prompt_versions (
                    tenant_id, prompt_id, version, system_prompt, developer_prompt,
                    user_prompt_template, variables_schema_json, output_schema_json,
                    example_inputs_json, example_outputs_json, model_preferences_json,
                    render_engine, status, creator, creator_id, editor, editor_id,
                    create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, prompt_id, *values[:11], actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            saved_id = inserted_id(conn, cursor, "prompt_versions", timestamp, actor)
    return get_prompt_version(tenant_id=tenant_id, version_id=saved_id)


def set_prompt_version_status(
    *,
    tenant_id: int,
    prompt_id: int,
    version_id: int,
    status: str,
    published_time: str | None,
    actor: str,
    actor_id: int | None,
) -> PromptVersion | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_ai_assets_schema(conn)
        conn.execute(
            """
            UPDATE prompt_versions
            SET status = ?, published_time = COALESCE(?, published_time), editor = ?, editor_id = ?,
                update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND prompt_id = ? AND deleted = 0
            """,
            (status, published_time, actor, actor_id, timestamp, version_id, tenant_id, prompt_id),
        )
        if status == PROMPT_VERSION_STATUS_PUBLISHED:
            conn.execute(
                """
                UPDATE prompt_versions
                SET status = ?, editor = ?, editor_id = ?, update_time = ?,
                    lock_version = lock_version + 1
                WHERE tenant_id = ? AND prompt_id = ? AND id <> ? AND status = ?
                    AND deleted = 0
                """,
                (
                    PROMPT_VERSION_STATUS_DEPRECATED,
                    actor,
                    actor_id,
                    timestamp,
                    tenant_id,
                    prompt_id,
                    version_id,
                    PROMPT_VERSION_STATUS_PUBLISHED,
                ),
            )
            conn.execute(
                """
                UPDATE prompt_assets
                SET status = 'published', editor = ?, editor_id = ?, update_time = ?,
                    lock_version = lock_version + 1
                WHERE id = ? AND tenant_id = ? AND deleted = 0
                """,
                (actor, actor_id, timestamp, prompt_id, tenant_id),
            )
    return get_prompt_version(tenant_id=tenant_id, version_id=version_id)


def inserted_id(conn: Any, cursor: Any, table_name: str, timestamp: str, actor: str) -> int:
    row_id = int(getattr(cursor, "lastrowid", 0) or 0)
    if row_id:
        return row_id
    row = conn.execute(
        f"""
        SELECT id
        FROM {table_name}
        WHERE create_time = ? AND creator = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (timestamp, actor),
    ).fetchone()
    return int(row["id"])


def count_row(cursor: Any) -> int:
    row = cursor.fetchone()
    return int(row["total"] if row else 0)


def row_to_asset(row: dict[str, Any]) -> PromptAsset:
    return PromptAsset(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        prompt_key=str(row.get("prompt_key") or ""),
        name=str(row.get("name") or ""),
        description=str(row.get("description") or ""),
        tags=decode_json_list(row.get("tags_json")),
        status=str(row.get("effective_status") or row.get("status") or "draft"),
        version_count=int(row.get("version_count") or 0),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_version(row: dict[str, Any]) -> PromptVersion:
    return PromptVersion(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        prompt_id=int(row["prompt_id"]),
        version=str(row.get("version") or ""),
        system_prompt=str(row.get("system_prompt") or ""),
        developer_prompt=str(row.get("developer_prompt") or ""),
        user_prompt_template=str(row.get("user_prompt_template") or ""),
        variables_schema=decode_json_dict(row.get("variables_schema_json")),
        output_schema=decode_json_dict(row.get("output_schema_json")),
        example_inputs=decode_json_list_of_dict(row.get("example_inputs_json")),
        example_outputs=decode_json_list_of_dict(row.get("example_outputs_json")),
        model_preferences=decode_json_dict(row.get("model_preferences_json")),
        render_engine=str(row.get("render_engine") or "simple"),
        status=str(row.get("status") or "draft"),
        published_time=str(row["published_time"]) if row.get("published_time") is not None else None,
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def encode_json_dict(value: Any) -> str:
    payload = value if isinstance(value, dict) else {}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def encode_json_list(value: Any) -> str:
    payload = value if isinstance(value, list) else []
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def encode_json_list_of_dict(value: Any) -> str:
    if not isinstance(value, list):
        return "[]"
    payload = [item for item in value if isinstance(item, dict)]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def decode_json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def decode_json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if not value:
        return []
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return [str(item) for item in payload] if isinstance(payload, list) else []


def decode_json_list_of_dict(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if not value:
        return []
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return [dict(item) for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []
