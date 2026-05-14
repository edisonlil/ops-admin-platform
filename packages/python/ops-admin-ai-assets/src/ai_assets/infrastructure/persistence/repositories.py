from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_assets.domain.models import PromptAsset, PromptVersion
from ai_assets.infrastructure.persistence.bootstrap import require_ai_assets_schema
from system.application.database import connect, resolve_database_url, resolve_db_path


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def list_prompt_assets(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    keyword: str = "",
    status: str = "",
) -> tuple[list[PromptAsset], int]:
    start = (page - 1) * page_size
    filters = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    if keyword:
        filters.append("(prompt_key LIKE ? OR name LIKE ? OR description LIKE ? OR tags_json LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like, like, like])
    if status:
        filters.append("status = ?")
        params.append(status)
    where_sql = " AND ".join(filters)
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM prompt_assets WHERE {where_sql}", tuple(params)))
        rows = conn.execute(
            f"""
            SELECT pa.*,
                   (SELECT COUNT(*) FROM prompt_versions pv
                    WHERE pv.prompt_id = pa.id AND pv.tenant_id = pa.tenant_id AND pv.deleted = 0) AS version_count
            FROM prompt_assets pa
            WHERE {where_sql}
            ORDER BY pa.update_time DESC, pa.id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, start),
        ).fetchall()
    return [row_to_asset(dict(row)) for row in rows], total


def get_prompt_asset(*, tenant_id: int, prompt_id: int) -> PromptAsset | None:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            """
            SELECT pa.*,
                   (SELECT COUNT(*) FROM prompt_versions pv
                    WHERE pv.prompt_id = pa.id AND pv.tenant_id = pa.tenant_id AND pv.deleted = 0) AS version_count
            FROM prompt_assets pa
            WHERE pa.id = ? AND pa.tenant_id = ? AND pa.deleted = 0
            """,
            (prompt_id, tenant_id),
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
                    status = ?, editor = ?, editor_id = ?,
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
                    status, creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, *values[:5], actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            saved_id = inserted_id(conn, cursor, "prompt_assets", timestamp, actor)
    return get_prompt_asset(tenant_id=tenant_id, prompt_id=saved_id)


def delete_prompt_asset(*, tenant_id: int, prompt_id: int, actor: str, actor_id: int | None) -> bool:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_ai_assets_schema(conn)
        cursor = conn.execute(
            """
            UPDATE prompt_assets
            SET deleted = 1, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (actor, actor_id, timestamp, prompt_id, tenant_id),
        )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


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
        if status == "published":
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
        status=str(row.get("status") or "draft"),
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
