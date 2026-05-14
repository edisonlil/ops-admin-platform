from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_assets.domain.models import (
    PROMPT_RUN_STATUS_FAILED,
    PromptAsset,
    PromptBinding,
    PromptRun,
    PromptTaskContract,
    PromptVersion,
)
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
        filters.append("(prompt_key LIKE ? OR name LIKE ? OR description LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like, like])
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
                    WHERE pv.prompt_id = pa.id AND pv.tenant_id = pa.tenant_id AND pv.deleted = 0) AS version_count,
                   (SELECT COUNT(*) FROM prompt_task_bindings pb
                    WHERE pb.prompt_id = pa.id AND pb.tenant_id = pa.tenant_id AND pb.deleted = 0) AS binding_count
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
                    WHERE pv.prompt_id = pa.id AND pv.tenant_id = pa.tenant_id AND pv.deleted = 0) AS version_count,
                   (SELECT COUNT(*) FROM prompt_task_bindings pb
                    WHERE pb.prompt_id = pa.id AND pb.tenant_id = pa.tenant_id AND pb.deleted = 0) AS binding_count
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


def list_contracts(
    *, tenant_id: int, page: int, page_size: int, keyword: str = "", owner_context: str = "", enabled: bool | None = None
) -> tuple[list[PromptTaskContract], int]:
    start = (page - 1) * page_size
    filters = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    if keyword:
        filters.append("(contract_key LIKE ? OR display_name LIKE ? OR description LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like, like])
    if owner_context:
        filters.append("owner_context = ?")
        params.append(owner_context)
    if enabled is not None:
        filters.append("enabled = ?")
        params.append(enabled)
    where_sql = " AND ".join(filters)
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM prompt_task_contracts WHERE {where_sql}", tuple(params)))
        rows = conn.execute(
            f"""
            SELECT *
            FROM prompt_task_contracts
            WHERE {where_sql}
            ORDER BY update_time DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, start),
        ).fetchall()
    return [row_to_contract(dict(row)) for row in rows], total


def get_contract_by_key(*, tenant_id: int, contract_key: str) -> PromptTaskContract | None:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            """
            SELECT *
            FROM prompt_task_contracts
            WHERE tenant_id = ? AND contract_key = ? AND deleted = 0
            """,
            (tenant_id, contract_key),
        ).fetchone()
    return row_to_contract(dict(row)) if row else None


def get_contract(*, tenant_id: int, contract_id: int) -> PromptTaskContract | None:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            "SELECT * FROM prompt_task_contracts WHERE tenant_id = ? AND id = ? AND deleted = 0",
            (tenant_id, contract_id),
        ).fetchone()
    return row_to_contract(dict(row)) if row else None


def save_contract(
    *, tenant_id: int, contract_key: str | None, payload: dict[str, Any], actor: str, actor_id: int | None
) -> PromptTaskContract | None:
    timestamp = now_iso()
    key = str(contract_key or payload["contract_key"])
    values = (
        key,
        str(payload.get("owner_context") or "general"),
        str(payload.get("task_kind") or "single_call"),
        str(payload.get("display_name") or key),
        str(payload.get("description") or ""),
        str(payload.get("llm_task_key") or key),
        encode_json_dict(payload.get("input_schema")),
        encode_json_dict(payload.get("output_schema")),
        encode_json_list(payload.get("required_capabilities") if isinstance(payload.get("required_capabilities"), list) else []),
        encode_json_dict(payload.get("allowed_prompt_scopes")),
        bool(payload.get("enabled", True)),
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_ai_assets_schema(conn)
        existing = conn.execute(
            "SELECT id FROM prompt_task_contracts WHERE tenant_id = ? AND contract_key = ? AND deleted = 0",
            (tenant_id, key),
        ).fetchone()
        if existing:
            contract_id = int(existing["id"])
            conn.execute(
                """
                UPDATE prompt_task_contracts
                SET contract_key = ?, owner_context = ?, task_kind = ?, display_name = ?,
                    description = ?, llm_task_key = ?, input_schema_json = ?, output_schema_json = ?,
                    required_capabilities_json = ?, allowed_prompt_scopes_json = ?, enabled = ?,
                    editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
                WHERE id = ? AND tenant_id = ? AND deleted = 0
                """,
                (*values, contract_id, tenant_id),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO prompt_task_contracts (
                    tenant_id, contract_key, owner_context, task_kind, display_name, description,
                    llm_task_key, input_schema_json, output_schema_json, required_capabilities_json,
                    allowed_prompt_scopes_json, enabled, creator, creator_id, editor, editor_id,
                    create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, *values[:11], actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            contract_id = inserted_id(conn, cursor, "prompt_task_contracts", timestamp, actor)
    return get_contract(tenant_id=tenant_id, contract_id=contract_id)


def list_prompt_versions_for_compatibility(*, tenant_id: int) -> list[tuple[PromptAsset, PromptVersion]]:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        rows = conn.execute(
            """
            SELECT pa.id AS asset_id, pa.tenant_id AS asset_tenant_id, pa.prompt_key, pa.name,
                   pa.description, pa.tags_json, pa.status AS asset_status,
                   pa.create_time AS asset_create_time,
                   pa.update_time AS asset_update_time,
                   0 AS version_count, 0 AS binding_count,
                   pv.*
            FROM prompt_assets pa
            JOIN prompt_versions pv ON pv.prompt_id = pa.id AND pv.tenant_id = pa.tenant_id
            WHERE pa.tenant_id = ? AND pa.deleted = 0 AND pv.deleted = 0
            ORDER BY pa.prompt_key ASC, pv.id DESC
            """,
            (tenant_id,),
        ).fetchall()
    items: list[tuple[PromptAsset, PromptVersion]] = []
    for row in rows:
        data = dict(row)
        asset_row = {
            "id": data["asset_id"],
            "tenant_id": data["asset_tenant_id"],
            "prompt_key": data["prompt_key"],
            "name": data["name"],
            "description": data["description"],
            "tags_json": data["tags_json"],
            "status": data["asset_status"],
            "version_count": data["version_count"],
            "binding_count": data["binding_count"],
            "create_time": data["asset_create_time"],
            "update_time": data["asset_update_time"],
        }
        items.append((row_to_asset(asset_row), row_to_version(data)))
    return items


def list_bindings(
    *, tenant_id: int, page: int, page_size: int, contract_key: str = "", environment: str = ""
) -> tuple[list[PromptBinding], int]:
    start = (page - 1) * page_size
    filters = ["pb.tenant_id = ?", "pb.deleted = 0"]
    params: list[Any] = [tenant_id]
    if contract_key:
        filters.append("pc.contract_key = ?")
        params.append(contract_key)
    if environment:
        filters.append("pb.environment = ?")
        params.append(environment)
    where_sql = " AND ".join(filters)
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        total = count_row(
            conn.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM prompt_task_bindings pb
                JOIN prompt_task_contracts pc ON pc.id = pb.contract_id
                WHERE {where_sql}
                """,
                tuple(params),
            )
        )
        rows = conn.execute(
            f"""
            SELECT pb.*, pc.contract_key, pa.prompt_key, pa.name AS prompt_name, pv.version AS prompt_version
            FROM prompt_task_bindings pb
            JOIN prompt_task_contracts pc ON pc.id = pb.contract_id AND pc.deleted = 0
            JOIN prompt_assets pa ON pa.id = pb.prompt_id AND pa.deleted = 0
            JOIN prompt_versions pv ON pv.id = pb.prompt_version_id AND pv.deleted = 0
            WHERE {where_sql}
            ORDER BY pb.enabled DESC, pb.priority ASC, pb.update_time DESC, pb.id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, start),
        ).fetchall()
    return [row_to_binding(dict(row)) for row in rows], total


def get_binding(*, tenant_id: int, binding_id: int) -> PromptBinding | None:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            """
            SELECT pb.*, pc.contract_key, pa.prompt_key, pa.name AS prompt_name, pv.version AS prompt_version
            FROM prompt_task_bindings pb
            JOIN prompt_task_contracts pc ON pc.id = pb.contract_id AND pc.deleted = 0
            JOIN prompt_assets pa ON pa.id = pb.prompt_id AND pa.deleted = 0
            JOIN prompt_versions pv ON pv.id = pb.prompt_version_id AND pv.deleted = 0
            WHERE pb.tenant_id = ? AND pb.id = ? AND pb.deleted = 0
            """,
            (tenant_id, binding_id),
        ).fetchone()
    return row_to_binding(dict(row)) if row else None


def effective_binding(*, tenant_id: int, contract_id: int, environment: str = "prod") -> PromptBinding | None:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            """
            SELECT pb.*, pc.contract_key, pa.prompt_key, pa.name AS prompt_name, pv.version AS prompt_version
            FROM prompt_task_bindings pb
            JOIN prompt_task_contracts pc ON pc.id = pb.contract_id AND pc.deleted = 0
            JOIN prompt_assets pa ON pa.id = pb.prompt_id AND pa.deleted = 0
            JOIN prompt_versions pv ON pv.id = pb.prompt_version_id AND pv.deleted = 0
            WHERE pb.tenant_id = ? AND pb.contract_id = ? AND pb.enabled = 1 AND pb.deleted = 0
              AND pb.environment IN (?, 'prod', 'dev')
              AND (pb.effective_from IS NULL OR pb.effective_from <= ?)
              AND (pb.effective_to IS NULL OR pb.effective_to >= ?)
            ORDER BY CASE WHEN pb.environment = ? THEN 0 ELSE 1 END, pb.priority ASC, pb.id DESC
            LIMIT 1
            """,
            (tenant_id, contract_id, environment, now_iso(), now_iso(), environment),
        ).fetchone()
    return row_to_binding(dict(row)) if row else None


def save_binding(
    *, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None
) -> PromptBinding | None:
    timestamp = now_iso()
    values = (
        int(payload["contract_id"]),
        int(payload["prompt_id"]),
        int(payload["prompt_version_id"]),
        str(payload.get("binding_name") or ""),
        int(payload.get("priority") or 100),
        str(payload.get("environment") or "dev"),
        bool(payload.get("enabled", True)),
        payload.get("effective_from"),
        payload.get("effective_to"),
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_ai_assets_schema(conn)
        cursor = conn.execute(
            """
            INSERT INTO prompt_task_bindings (
                tenant_id, contract_id, prompt_id, prompt_version_id, binding_name, priority,
                environment, enabled, effective_from, effective_to, creator, creator_id,
                editor, editor_id, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, *values[:9], actor, actor_id, actor, actor_id, timestamp, timestamp),
        )
        binding_id = inserted_id(conn, cursor, "prompt_task_bindings", timestamp, actor)
    return get_binding(tenant_id=tenant_id, binding_id=binding_id)


def set_binding_enabled(
    *, tenant_id: int, binding_id: int, enabled: bool, actor: str, actor_id: int | None
) -> PromptBinding | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_ai_assets_schema(conn)
        conn.execute(
            """
            UPDATE prompt_task_bindings
            SET enabled = ?, editor = ?, editor_id = ?, update_time = ?,
                lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (enabled, actor, actor_id, timestamp, binding_id, tenant_id),
        )
    return get_binding(tenant_id=tenant_id, binding_id=binding_id)


def create_run(
    *,
    tenant_id: int,
    payload: dict[str, Any],
    actor: str,
    actor_id: int | None,
) -> PromptRun:
    timestamp = now_iso()
    status = str(payload.get("status") or PROMPT_RUN_STATUS_FAILED)
    with connect(database_target(), readonly=False) as conn:
        require_ai_assets_schema(conn)
        cursor = conn.execute(
            """
            INSERT INTO prompt_runs (
                tenant_id, contract_key, prompt_id, prompt_version_id, llm_task_key, input_json,
                rendered_messages_json, output_text, output_json, schema_valid,
                validation_errors_json, status, elapsed_ms, request_id, correlation_id,
                creator, creator_id, editor, editor_id, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                str(payload.get("contract_key") or ""),
                payload.get("prompt_id"),
                payload.get("prompt_version_id"),
                str(payload.get("llm_task_key") or ""),
                encode_json_dict(payload.get("input")),
                encode_json_list_of_dict(payload.get("rendered_messages")),
                str(payload.get("output_text") or ""),
                encode_optional_json_dict(payload.get("output_json")),
                bool(payload.get("schema_valid", False)),
                encode_json_list(payload.get("validation_errors") if isinstance(payload.get("validation_errors"), list) else []),
                status,
                int(payload.get("elapsed_ms") or 0),
                str(payload.get("request_id") or ""),
                str(payload.get("correlation_id") or ""),
                actor,
                actor_id,
                actor,
                actor_id,
                timestamp,
                timestamp,
            ),
        )
        run_id = inserted_id(conn, cursor, "prompt_runs", timestamp, actor)
        row = conn.execute("SELECT * FROM prompt_runs WHERE id = ?", (run_id,)).fetchone()
    return row_to_run(dict(row))


def list_runs(
    *, tenant_id: int, page: int, page_size: int, contract_key: str = "", status: str = ""
) -> tuple[list[PromptRun], int]:
    start = (page - 1) * page_size
    filters = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    if contract_key:
        filters.append("contract_key = ?")
        params.append(contract_key)
    if status:
        filters.append("status = ?")
        params.append(status)
    where_sql = " AND ".join(filters)
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM prompt_runs WHERE {where_sql}", tuple(params)))
        rows = conn.execute(
            f"""
            SELECT *
            FROM prompt_runs
            WHERE {where_sql}
            ORDER BY create_time DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, start),
        ).fetchall()
    return [row_to_run(dict(row)) for row in rows], total


def get_run(*, tenant_id: int, run_id: int) -> PromptRun | None:
    with connect(database_target(), readonly=True) as conn:
        require_ai_assets_schema(conn)
        row = conn.execute(
            "SELECT * FROM prompt_runs WHERE tenant_id = ? AND id = ? AND deleted = 0",
            (tenant_id, run_id),
        ).fetchone()
    return row_to_run(dict(row)) if row else None


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
        binding_count=int(row.get("binding_count") or 0),
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


def row_to_contract(row: dict[str, Any]) -> PromptTaskContract:
    return PromptTaskContract(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        contract_key=str(row.get("contract_key") or ""),
        owner_context=str(row.get("owner_context") or "general"),
        task_kind=str(row.get("task_kind") or "single_call"),
        display_name=str(row.get("display_name") or ""),
        description=str(row.get("description") or ""),
        llm_task_key=str(row.get("llm_task_key") or ""),
        input_schema=decode_json_dict(row.get("input_schema_json")),
        output_schema=decode_json_dict(row.get("output_schema_json")),
        required_capabilities=decode_json_list(row.get("required_capabilities_json")),
        allowed_prompt_scopes=decode_json_dict(row.get("allowed_prompt_scopes_json")),
        enabled=bool(row.get("enabled")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_binding(row: dict[str, Any]) -> PromptBinding:
    return PromptBinding(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        contract_id=int(row["contract_id"]),
        contract_key=str(row.get("contract_key") or ""),
        prompt_id=int(row["prompt_id"]),
        prompt_key=str(row.get("prompt_key") or ""),
        prompt_name=str(row.get("prompt_name") or ""),
        prompt_version_id=int(row["prompt_version_id"]),
        prompt_version=str(row.get("prompt_version") or ""),
        binding_name=str(row.get("binding_name") or ""),
        priority=int(row.get("priority") or 100),
        environment=str(row.get("environment") or "dev"),
        enabled=bool(row.get("enabled")),
        effective_from=str(row["effective_from"]) if row.get("effective_from") is not None else None,
        effective_to=str(row["effective_to"]) if row.get("effective_to") is not None else None,
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_run(row: dict[str, Any]) -> PromptRun:
    output_json = None if row.get("output_json") is None else decode_json_dict(row.get("output_json"))
    return PromptRun(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        contract_key=str(row.get("contract_key") or ""),
        prompt_id=int(row["prompt_id"]) if row.get("prompt_id") is not None else None,
        prompt_version_id=int(row["prompt_version_id"]) if row.get("prompt_version_id") is not None else None,
        llm_task_key=str(row.get("llm_task_key") or ""),
        input=decode_json_dict(row.get("input_json")),
        rendered_messages=decode_json_list_of_str_dict(row.get("rendered_messages_json")),
        output_text=str(row.get("output_text") or ""),
        output_json=output_json,
        schema_valid=bool(row.get("schema_valid")),
        validation_errors=decode_json_list(row.get("validation_errors_json")),
        status=str(row.get("status") or "failed"),
        elapsed_ms=int(row.get("elapsed_ms") or 0),
        request_id=str(row.get("request_id") or ""),
        correlation_id=str(row.get("correlation_id") or ""),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def encode_json_dict(value: Any) -> str:
    payload = value if isinstance(value, dict) else {}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def encode_optional_json_dict(value: Any) -> str | None:
    if value is None:
        return None
    return encode_json_dict(value)


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


def decode_json_list_of_str_dict(value: Any) -> list[dict[str, str]]:
    return [
        {str(key): str(val) for key, val in item.items()}
        for item in decode_json_list_of_dict(value)
    ]
