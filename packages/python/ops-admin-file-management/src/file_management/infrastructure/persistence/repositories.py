from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from file_management.domain.models import (
    FILE_STATUS_AVAILABLE,
    FILE_STATUS_DELETED,
    FileAccessLog,
    FileFolder,
    FileLibrary,
    PreviewProfile,
    FileSearchIndexJob,
    ManagedFile,
    StorageProfile,
    StorageUsage,
    TenantStorageQuota,
)
from file_management.infrastructure.persistence.bootstrap import require_file_management_schema
from system.application.data_access import DataAccessPredicate, ResourceDescriptor, apply_data_access
from system.application.database import connect, resolve_database_url, resolve_db_path
from system.application.sorting import build_order_by, parse_sort_params


LIBRARY_SORT_COLUMNS = {
    "id": "id",
    "name": "name",
    "library_type": "library_type",
    "visibility": "visibility",
    "status": "status",
    "create_time": "create_time",
    "update_time": "update_time",
}
FILE_SORT_COLUMNS = {
    "id": "id",
    "original_name": "original_name",
    "display_name": "display_name",
    "extension": "extension",
    "mime_type": "mime_type",
    "size_bytes": "size_bytes",
    "status": "status",
    "visibility": "visibility",
    "indexed_at": "indexed_at",
    "create_time": "create_time",
    "update_time": "update_time",
}
ACCESS_LOG_SORT_COLUMNS = {
    "id": "id",
    "file_id": "file_id",
    "action": "action",
    "actor_user_id": "actor_user_id",
    "actor_name": "actor_name",
    "result": "result",
    "create_time": "create_time",
}
INDEX_JOB_SORT_COLUMNS = {
    "id": "id",
    "file_id": "file_id",
    "job_type": "job_type",
    "status": "status",
    "attempts": "attempts",
    "scheduled_time": "scheduled_time",
    "finished_time": "finished_time",
    "create_time": "create_time",
    "update_time": "update_time",
}
STORAGE_PROFILE_SORT_COLUMNS = {
    "id": "id",
    "provider": "provider",
    "name": "name",
    "endpoint": "endpoint",
    "bucket": "bucket",
    "is_default": "is_default",
    "enabled": "enabled",
    "create_time": "create_time",
    "update_time": "update_time",
}
PREVIEW_PROFILE_SORT_COLUMNS = {
    "id": "id",
    "provider": "provider",
    "name": "name",
    "base_url": "base_url",
    "is_default": "is_default",
    "enabled": "enabled",
    "create_time": "create_time",
    "update_time": "update_time",
}


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


FILE_OBJECT_RESOURCE = ResourceDescriptor(resource_key="file.object")


def next_file_id() -> int:
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        cursor = conn.execute(
            """
            INSERT INTO file_objects (
                tenant_id, original_name, display_name, storage_key, status,
                creator, editor, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (0, "__reserved__", "__reserved__", "__reserved__", FILE_STATUS_DELETED, "system", "system", now_iso(), now_iso()),
        )
        file_id = int(getattr(cursor, "lastrowid", 0) or 0)
        if not file_id:
            row = conn.execute("SELECT MAX(id) AS id FROM file_objects").fetchone()
            file_id = int(row["id"])
        conn.execute("DELETE FROM file_objects WHERE id = ?", (file_id,))
    return file_id


def list_libraries(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> tuple[list[FileLibrary], int]:
    offset = (page - 1) * page_size
    order_by = build_order_by(
        parse_sort_params(sort_by, sort_dir),
        allowed=LIBRARY_SORT_COLUMNS,
        default="update_time DESC, id DESC",
        tie_breaker="id DESC",
    )
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        total = count_row(
            conn.execute(
                "SELECT COUNT(*) AS total FROM file_libraries WHERE tenant_id = ? AND deleted = 0",
                (tenant_id,),
            )
        )
        rows = conn.execute(
            f"""
            SELECT *
            FROM file_libraries
            WHERE tenant_id = ? AND deleted = 0
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (tenant_id, page_size, offset),
        ).fetchall()
    return [row_to_library(dict(row)) for row in rows], total


def get_library(*, tenant_id: int, library_id: int) -> FileLibrary | None:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            "SELECT * FROM file_libraries WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (library_id, tenant_id),
        ).fetchone()
    return row_to_library(dict(row)) if row else None


def save_library(
    *, tenant_id: int, library_id: int | None, payload: dict[str, Any], actor: str, actor_id: int | None
) -> FileLibrary | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        values = (
            str(payload["name"]),
            str(payload.get("description") or ""),
            str(payload.get("library_type") or "general"),
            str(payload.get("visibility") or "tenant"),
            str(payload.get("status") or "active"),
            actor,
            actor_id,
            timestamp,
        )
        if library_id:
            conn.execute(
                """
                UPDATE file_libraries
                SET name = ?, description = ?, library_type = ?, visibility = ?, status = ?,
                    editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
                WHERE id = ? AND tenant_id = ? AND deleted = 0
                """,
                (*values, library_id, tenant_id),
            )
            saved_id = library_id
        else:
            cursor = conn.execute(
                """
                INSERT INTO file_libraries (
                    tenant_id, name, description, library_type, visibility, status,
                    creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, *values[:5], actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            saved_id = inserted_id(conn, cursor, "file_libraries", timestamp, actor)
        row = conn.execute(
            "SELECT * FROM file_libraries WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (saved_id, tenant_id),
        ).fetchone()
    return row_to_library(dict(row)) if row else None


def library_file_count(*, tenant_id: int, library_id: int) -> int:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM file_objects
            WHERE tenant_id = ? AND library_id = ? AND deleted = 0
            """,
            (tenant_id, library_id),
        ).fetchone()
    return int(row["total"] if row else 0)


def library_folder_count(*, tenant_id: int, library_id: int) -> int:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM file_folders
            WHERE tenant_id = ? AND library_id = ? AND deleted = 0
            """,
            (tenant_id, library_id),
        ).fetchone()
    return int(row["total"] if row else 0)


def delete_library(*, tenant_id: int, library_id: int, actor: str, actor_id: int | None) -> bool:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        cursor = conn.execute(
            """
            UPDATE file_libraries
            SET deleted = 1, active_marker = NULL, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (actor, actor_id, timestamp, library_id, tenant_id),
        )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def list_folders(*, tenant_id: int, library_id: int, parent_id: int | None = None) -> list[FileFolder]:
    filters = ["tenant_id = ?", "library_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id, library_id]
    if parent_id is None:
        filters.append("parent_id IS NULL")
    else:
        filters.append("parent_id = ?")
        params.append(parent_id)
    where_sql = " AND ".join(filters)
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM file_folders
            WHERE {where_sql}
            ORDER BY name ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
    return [row_to_folder(dict(row)) for row in rows]


def list_all_folders(*, tenant_id: int, library_id: int) -> list[FileFolder]:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        rows = conn.execute(
            """
            SELECT *
            FROM file_folders
            WHERE tenant_id = ? AND library_id = ? AND deleted = 0
            ORDER BY parent_id ASC, name ASC, id ASC
            """,
            (tenant_id, library_id),
        ).fetchall()
    return [row_to_folder(dict(row)) for row in rows]


def get_folder(*, tenant_id: int, folder_id: int) -> FileFolder | None:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            "SELECT * FROM file_folders WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (folder_id, tenant_id),
        ).fetchone()
    return row_to_folder(dict(row)) if row else None


def save_folder(
    *, tenant_id: int, folder_id: int | None, payload: dict[str, Any], actor: str, actor_id: int | None
) -> FileFolder | None:
    timestamp = now_iso()
    library_id = int(payload["library_id"])
    parent_id = int(payload["parent_id"]) if payload.get("parent_id") is not None else None
    values = (
        library_id,
        parent_id,
        str(payload["name"]),
        str(payload.get("description") or ""),
        str(payload.get("status") or "active"),
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        if folder_id:
            conn.execute(
                """
                UPDATE file_folders
                SET library_id = ?, parent_id = ?, name = ?, description = ?, status = ?,
                    editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
                WHERE id = ? AND tenant_id = ? AND deleted = 0
                """,
                (*values, folder_id, tenant_id),
            )
            saved_id = folder_id
        else:
            cursor = conn.execute(
                """
                INSERT INTO file_folders (
                    tenant_id, library_id, parent_id, name, description, status,
                    creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, *values[:5], actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            saved_id = inserted_id(conn, cursor, "file_folders", timestamp, actor)
        row = conn.execute(
            "SELECT * FROM file_folders WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (saved_id, tenant_id),
        ).fetchone()
    return row_to_folder(dict(row)) if row else None


def folder_child_count(*, tenant_id: int, folder_id: int) -> int:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        folder_count = conn.execute(
            "SELECT COUNT(*) AS total FROM file_folders WHERE tenant_id = ? AND parent_id = ? AND deleted = 0",
            (tenant_id, folder_id),
        ).fetchone()
        file_count = conn.execute(
            "SELECT COUNT(*) AS total FROM file_objects WHERE tenant_id = ? AND folder_id = ? AND deleted = 0",
            (tenant_id, folder_id),
        ).fetchone()
    return int(folder_count["total"] if folder_count else 0) + int(file_count["total"] if file_count else 0)


def folder_storage_usages(*, tenant_id: int, library_id: int, folder_ids: list[int]) -> dict[int, StorageUsage]:
    if not folder_ids:
        return {}
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        folder_rows = conn.execute(
            """
            SELECT id, parent_id
            FROM file_folders
            WHERE tenant_id = ? AND library_id = ? AND deleted = 0
            """,
            (tenant_id, library_id),
        ).fetchall()
        file_rows = conn.execute(
            """
            SELECT folder_id, COALESCE(SUM(size_bytes), 0) AS used_bytes, COUNT(*) AS file_count
            FROM file_objects
            WHERE tenant_id = ? AND library_id = ? AND deleted = 0 AND status = ? AND folder_id IS NOT NULL
            GROUP BY folder_id
            """,
            (tenant_id, library_id, FILE_STATUS_AVAILABLE),
        ).fetchall()

    child_ids_by_parent: dict[int, list[int]] = {}
    for row in folder_rows:
        if row["parent_id"] is None:
            continue
        child_ids_by_parent.setdefault(int(row["parent_id"]), []).append(int(row["id"]))

    direct_usage: dict[int, tuple[int, int]] = {}
    for row in file_rows:
        folder_id = int(row["folder_id"])
        direct_usage[folder_id] = (int(row["used_bytes"] or 0), int(row["file_count"] or 0))

    usage_cache: dict[int, tuple[int, int]] = {}

    def sum_folder(folder_id: int) -> tuple[int, int]:
        cached = usage_cache.get(folder_id)
        if cached is not None:
            return cached
        used_bytes, file_count = direct_usage.get(folder_id, (0, 0))
        for child_id in child_ids_by_parent.get(folder_id, []):
            child_used_bytes, child_file_count = sum_folder(child_id)
            used_bytes += child_used_bytes
            file_count += child_file_count
        usage_cache[folder_id] = (used_bytes, file_count)
        return usage_cache[folder_id]

    usages: dict[int, StorageUsage] = {}
    for folder_id in folder_ids:
        used_bytes, file_count = sum_folder(folder_id)
        usages[folder_id] = StorageUsage(tenant_id=tenant_id, used_bytes=used_bytes, file_count=file_count)
    return usages


def folder_storage_usage(*, tenant_id: int, library_id: int, folder_id: int) -> StorageUsage:
    return folder_storage_usages(tenant_id=tenant_id, library_id=library_id, folder_ids=[folder_id]).get(
        folder_id,
        StorageUsage(tenant_id=tenant_id, used_bytes=0, file_count=0),
    )


def delete_folder(*, tenant_id: int, folder_id: int, actor: str, actor_id: int | None) -> bool:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        cursor = conn.execute(
            """
            UPDATE file_folders
            SET deleted = 1, active_marker = NULL, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (actor, actor_id, timestamp, folder_id, tenant_id),
        )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def list_files(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    library_id: int | None = None,
    folder_id: int | None = None,
    current_folder_only: bool = False,
    keyword: str = "",
    mime_type: str = "",
    status: str = "",
    data_scope: DataAccessPredicate | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> tuple[list[ManagedFile], int]:
    offset = (page - 1) * page_size
    filters = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    apply_data_access(filters, params, data_scope=data_scope, resource=FILE_OBJECT_RESOURCE)
    if library_id is not None:
        filters.append("library_id = ?")
        params.append(library_id)
    if current_folder_only:
        if folder_id is None:
            filters.append("folder_id IS NULL")
        else:
            filters.append("folder_id = ?")
            params.append(folder_id)
    if keyword:
        filters.append("(original_name LIKE ? OR display_name LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like])
    if mime_type:
        filters.append("mime_type = ?")
        params.append(mime_type)
    if status:
        filters.append("status = ?")
        params.append(status)
    where_sql = " AND ".join(filters)
    order_by = build_order_by(
        parse_sort_params(sort_by, sort_dir),
        allowed=FILE_SORT_COLUMNS,
        default="update_time DESC, id DESC",
        tie_breaker="id DESC",
    )
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM file_objects WHERE {where_sql}", tuple(params)))
        rows = conn.execute(
            f"""
            SELECT *
            FROM file_objects
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, offset),
        ).fetchall()
    return [row_to_file(dict(row)) for row in rows], total


def get_file(*, tenant_id: int | None, file_id: int, data_scope: DataAccessPredicate | None = None) -> ManagedFile | None:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        filters = ["id = ?", "deleted = 0", "status = ?"]
        params: list[Any] = [file_id, FILE_STATUS_AVAILABLE]
        if tenant_id is None:
            row = conn.execute(
                f"""
                SELECT *
                FROM file_objects
                WHERE {" AND ".join(filters)}
                """,
                tuple(params),
            ).fetchone()
        else:
            filters.append("tenant_id = ?")
            params.append(tenant_id)
            apply_data_access(filters, params, data_scope=data_scope, resource=FILE_OBJECT_RESOURCE)
            row = conn.execute(
                f"""
                SELECT *
                FROM file_objects
                WHERE {" AND ".join(filters)}
                """,
                tuple(params),
            ).fetchone()
    return row_to_file(dict(row)) if row else None


def create_file(
    *,
    file_id: int,
    tenant_id: int,
    library_id: int | None,
    folder_id: int | None,
    original_name: str,
    display_name: str,
    extension: str,
    mime_type: str,
    size_bytes: int,
    sha256: str,
    storage_provider: str,
    storage_bucket: str,
    storage_key: str,
    visibility: str,
    metadata: dict[str, Any],
    actor: str,
    actor_id: int | None,
    owner_user_id: int | None = None,
    owner_department_id: int | None = None,
) -> ManagedFile:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        conn.execute(
            """
            INSERT INTO file_objects (
                id, tenant_id, library_id, folder_id, original_name, display_name, extension, mime_type,
                size_bytes, sha256, storage_provider, storage_bucket, storage_key, status,
                visibility, metadata_json, owner_user_id, owner_department_id, creator,
                creator_id, editor, editor_id, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                tenant_id,
                library_id,
                folder_id,
                original_name,
                display_name,
                extension,
                mime_type,
                size_bytes,
                sha256,
                storage_provider,
                storage_bucket,
                storage_key,
                FILE_STATUS_AVAILABLE,
                visibility,
                encode_json(metadata),
                owner_user_id,
                owner_department_id,
                actor,
                actor_id,
                actor,
                actor_id,
                timestamp,
                timestamp,
            ),
        )
        row = conn.execute("SELECT * FROM file_objects WHERE id = ?", (file_id,)).fetchone()
    return row_to_file(dict(row))


def delete_file(*, tenant_id: int, file_id: int, actor: str, actor_id: int | None) -> bool:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        cursor = conn.execute(
            """
            UPDATE file_objects
            SET deleted = 1, status = ?, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (FILE_STATUS_DELETED, actor, actor_id, timestamp, file_id, tenant_id),
        )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def mark_file_indexed(*, tenant_id: int, file_id: int) -> None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        conn.execute(
            """
            UPDATE file_objects
            SET indexed_at = ?, update_time = ?
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (timestamp, timestamp, file_id, tenant_id),
        )


def storage_usage(
    *,
    tenant_id: int,
    library_id: int | None = None,
    folder_id: int | None = None,
    current_folder_only: bool = False,
    keyword: str = "",
) -> StorageUsage:
    filters = ["tenant_id = ?", "deleted = 0", "status = ?"]
    params: list[Any] = [tenant_id, FILE_STATUS_AVAILABLE]
    if library_id is not None:
        filters.append("library_id = ?")
        params.append(library_id)
    if current_folder_only:
        if folder_id is None:
            filters.append("folder_id IS NULL")
        else:
            filters.append("folder_id = ?")
            params.append(folder_id)
    if keyword:
        filters.append("(original_name LIKE ? OR display_name LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like])
    where_sql = " AND ".join(filters)
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            f"""
            SELECT COALESCE(SUM(size_bytes), 0) AS used_bytes, COUNT(*) AS file_count
            FROM file_objects
            WHERE {where_sql}
            """,
            tuple(params),
        ).fetchone()
    return StorageUsage(
        tenant_id=tenant_id,
        used_bytes=int(row["used_bytes"] if row else 0),
        file_count=int(row["file_count"] if row else 0),
    )


def get_quota(*, tenant_id: int) -> TenantStorageQuota | None:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            "SELECT * FROM tenant_file_storage_quotas WHERE tenant_id = ? AND deleted = 0",
            (tenant_id,),
        ).fetchone()
    return row_to_quota(dict(row)) if row else None


def save_quota(
    *,
    tenant_id: int,
    quota_bytes: int,
    max_file_size_bytes: int,
    allowed_mime_types: list[str],
    blocked_extensions: list[str],
    enabled: bool,
    actor: str,
    actor_id: int | None,
) -> TenantStorageQuota:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        existing = conn.execute(
            "SELECT id FROM tenant_file_storage_quotas WHERE tenant_id = ? AND deleted = 0",
            (tenant_id,),
        ).fetchone()
        if existing:
            quota_id = int(existing["id"])
            conn.execute(
                """
                UPDATE tenant_file_storage_quotas
                SET quota_bytes = ?, max_file_size_bytes = ?, allowed_mime_types_json = ?,
                    blocked_extensions_json = ?, enabled = ?, editor = ?, editor_id = ?,
                    update_time = ?, lock_version = lock_version + 1
                WHERE id = ?
                """,
                (
                    quota_bytes,
                    max_file_size_bytes,
                    encode_json_list(allowed_mime_types),
                    encode_json_list(blocked_extensions),
                    enabled,
                    actor,
                    actor_id,
                    timestamp,
                    quota_id,
                ),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO tenant_file_storage_quotas (
                    tenant_id, quota_bytes, max_file_size_bytes, allowed_mime_types_json,
                    blocked_extensions_json, enabled, creator, creator_id, editor, editor_id,
                    create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    quota_bytes,
                    max_file_size_bytes,
                    encode_json_list(allowed_mime_types),
                    encode_json_list(blocked_extensions),
                    enabled,
                    actor,
                    actor_id,
                    actor,
                    actor_id,
                    timestamp,
                    timestamp,
                ),
            )
            quota_id = inserted_id(conn, cursor, "tenant_file_storage_quotas", timestamp, actor)
        row = conn.execute("SELECT * FROM tenant_file_storage_quotas WHERE id = ?", (quota_id,)).fetchone()
    return row_to_quota(dict(row))


def list_storage_profiles(sort_by: str | None = None, sort_dir: str | None = None) -> list[StorageProfile]:
    sort_spec = parse_sort_params(sort_by, sort_dir)
    order_by = build_order_by(sort_spec, allowed=STORAGE_PROFILE_SORT_COLUMNS, default="is_default DESC, provider ASC, id DESC")
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM file_storage_profiles
            WHERE deleted = 0
            ORDER BY {order_by}
            """
        ).fetchall()
    return [row_to_storage_profile(dict(row)) for row in rows]


def get_storage_profile(*, profile_id: int) -> StorageProfile | None:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            "SELECT * FROM file_storage_profiles WHERE id = ? AND deleted = 0",
            (profile_id,),
        ).fetchone()
    return row_to_storage_profile(dict(row)) if row else None


def get_default_storage_profile(provider: str = "minio") -> StorageProfile | None:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            """
            SELECT *
            FROM file_storage_profiles
            WHERE provider = ? AND is_default = 1 AND enabled = 1 AND deleted = 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (provider,),
        ).fetchone()
    return row_to_storage_profile(dict(row)) if row else None


def save_storage_profile(
    *, profile_id: int | None, payload: dict[str, Any], actor: str, actor_id: int | None
) -> StorageProfile:
    timestamp = now_iso()
    provider = str(payload.get("provider") or "minio")
    is_default = bool(payload.get("is_default", False))
    secret_access_key = str(payload.get("secret_access_key") or "")
    if profile_id and not secret_access_key:
        with connect(database_target(), readonly=True) as conn:
            require_file_management_schema(conn)
            existing = conn.execute(
                "SELECT secret_access_key_encrypted FROM file_storage_profiles WHERE id = ? AND deleted = 0",
                (profile_id,),
            ).fetchone()
        secret_access_key = str(existing["secret_access_key_encrypted"] or "") if existing else ""
    values = (
        provider,
        str(payload.get("name") or ""),
        str(payload.get("endpoint") or ""),
        str(payload.get("region") or ""),
        str(payload.get("bucket") or ""),
        str(payload.get("access_key_id") or ""),
        secret_access_key,
        bool(payload.get("path_style_enabled", True)),
        bool(payload.get("tls_enabled", True)),
        is_default,
        bool(payload.get("enabled", True)),
        encode_json(payload.get("extra_config") if isinstance(payload.get("extra_config"), dict) else {}),
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        if is_default:
            unset_default_profiles(conn, provider=provider, actor=actor, actor_id=actor_id, timestamp=timestamp)
        if profile_id:
            conn.execute(
                """
                UPDATE file_storage_profiles
                SET provider = ?, name = ?, endpoint = ?, region = ?, bucket = ?, access_key_id = ?,
                    secret_access_key_encrypted = ?, path_style_enabled = ?, tls_enabled = ?,
                    is_default = ?, enabled = ?, extra_config_json = ?, editor = ?, editor_id = ?,
                    update_time = ?, lock_version = lock_version + 1
                WHERE id = ? AND deleted = 0
                """,
                (*values, profile_id),
            )
            saved_id = profile_id
        else:
            cursor = conn.execute(
                """
                INSERT INTO file_storage_profiles (
                    tenant_id, provider, name, endpoint, region, bucket, access_key_id,
                    secret_access_key_encrypted, path_style_enabled, tls_enabled, is_default,
                    enabled, extra_config_json, creator, creator_id, editor, editor_id,
                    create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (0, *values[:12], actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            saved_id = inserted_id(conn, cursor, "file_storage_profiles", timestamp, actor)
        row = conn.execute("SELECT * FROM file_storage_profiles WHERE id = ?", (saved_id,)).fetchone()
    return row_to_storage_profile(dict(row))


def set_default_storage_profile(*, profile_id: int, actor: str, actor_id: int | None) -> StorageProfile | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            "SELECT provider FROM file_storage_profiles WHERE id = ? AND enabled = 1 AND deleted = 0",
            (profile_id,),
        ).fetchone()
        if not row:
            return None
        provider = str(row["provider"])
        unset_default_profiles(conn, provider=provider, actor=actor, actor_id=actor_id, timestamp=timestamp)
        conn.execute(
            """
            UPDATE file_storage_profiles
            SET is_default = 1, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ?
            """,
            (actor, actor_id, timestamp, profile_id),
        )
        saved = conn.execute("SELECT * FROM file_storage_profiles WHERE id = ?", (profile_id,)).fetchone()
    return row_to_storage_profile(dict(saved)) if saved else None


def list_preview_profiles(sort_by: str | None = None, sort_dir: str | None = None) -> list[PreviewProfile]:
    sort_spec = parse_sort_params(sort_by, sort_dir)
    order_by = build_order_by(sort_spec, allowed=PREVIEW_PROFILE_SORT_COLUMNS, default="is_default DESC, provider ASC, id DESC")
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM file_preview_profiles
            WHERE deleted = 0
            ORDER BY {order_by}
            """
        ).fetchall()
    return [row_to_preview_profile(dict(row)) for row in rows]


def get_preview_profile(*, profile_id: int) -> PreviewProfile | None:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            "SELECT * FROM file_preview_profiles WHERE id = ? AND deleted = 0",
            (profile_id,),
        ).fetchone()
    return row_to_preview_profile(dict(row)) if row else None


def get_default_preview_profile() -> PreviewProfile | None:
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            """
            SELECT *
            FROM file_preview_profiles
            WHERE is_default = 1 AND enabled = 1 AND deleted = 0
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    return row_to_preview_profile(dict(row)) if row else None


def save_preview_profile(
    *, profile_id: int | None, payload: dict[str, Any], actor: str, actor_id: int | None
) -> PreviewProfile:
    timestamp = now_iso()
    is_default = bool(payload.get("is_default", False))
    values = (
        str(payload.get("provider") or "kkfileview"),
        str(payload.get("name") or ""),
        str(payload.get("base_url") or ""),
        bool(payload.get("enabled", True)),
        is_default,
        encode_json_list(normalize_string_list(payload.get("supported_extensions"))),
        encode_json(payload.get("config") if isinstance(payload.get("config"), dict) else {}),
        actor,
        actor_id,
        timestamp,
    )
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        if is_default:
            unset_default_preview_profiles(conn, actor=actor, actor_id=actor_id, timestamp=timestamp)
        if profile_id:
            conn.execute(
                """
                UPDATE file_preview_profiles
                SET provider = ?, name = ?, base_url = ?, enabled = ?, is_default = ?,
                    supported_extensions_json = ?, config_json = ?, editor = ?, editor_id = ?,
                    update_time = ?, lock_version = lock_version + 1
                WHERE id = ? AND deleted = 0
                """,
                (*values, profile_id),
            )
            saved_id = profile_id
        else:
            cursor = conn.execute(
                """
                INSERT INTO file_preview_profiles (
                    tenant_id, provider, name, base_url, enabled, is_default,
                    supported_extensions_json, config_json, creator, creator_id,
                    editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (0, *values[:7], actor, actor_id, actor, actor_id, timestamp, timestamp),
            )
            saved_id = inserted_id(conn, cursor, "file_preview_profiles", timestamp, actor)
        row = conn.execute("SELECT * FROM file_preview_profiles WHERE id = ?", (saved_id,)).fetchone()
    return row_to_preview_profile(dict(row))


def set_default_preview_profile(*, profile_id: int, actor: str, actor_id: int | None) -> PreviewProfile | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        row = conn.execute(
            "SELECT id FROM file_preview_profiles WHERE id = ? AND enabled = 1 AND deleted = 0",
            (profile_id,),
        ).fetchone()
        if not row:
            return None
        unset_default_preview_profiles(conn, actor=actor, actor_id=actor_id, timestamp=timestamp)
        conn.execute(
            """
            UPDATE file_preview_profiles
            SET is_default = 1, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ?
            """,
            (actor, actor_id, timestamp, profile_id),
        )
        saved = conn.execute("SELECT * FROM file_preview_profiles WHERE id = ?", (profile_id,)).fetchone()
    return row_to_preview_profile(dict(saved)) if saved else None


def record_access_log(
    *,
    tenant_id: int,
    file_id: int | None,
    action: str,
    result: str,
    actor: str,
    actor_id: int | None,
    client_ip: str = "",
    user_agent: str = "",
    detail: dict[str, Any] | None = None,
) -> FileAccessLog:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        cursor = conn.execute(
            """
            INSERT INTO file_access_logs (
                tenant_id, file_id, action, actor_user_id, actor_name, client_ip, user_agent,
                result, detail_json, creator, creator_id, editor, editor_id, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                file_id,
                action,
                actor_id,
                actor,
                client_ip,
                user_agent,
                result,
                encode_json(detail or {}),
                actor,
                actor_id,
                actor,
                actor_id,
                timestamp,
                timestamp,
            ),
        )
        log_id = inserted_id(conn, cursor, "file_access_logs", timestamp, actor)
        row = conn.execute("SELECT * FROM file_access_logs WHERE id = ?", (log_id,)).fetchone()
    return row_to_access_log(dict(row))


def list_access_logs(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    file_id: int | None = None,
    action: str = "",
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> tuple[list[FileAccessLog], int]:
    offset = (page - 1) * page_size
    filters = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    if file_id is not None:
        filters.append("file_id = ?")
        params.append(file_id)
    if action:
        filters.append("action = ?")
        params.append(action)
    where_sql = " AND ".join(filters)
    order_by = build_order_by(
        parse_sort_params(sort_by, sort_dir),
        allowed=ACCESS_LOG_SORT_COLUMNS,
        default="create_time DESC, id DESC",
        tie_breaker="id DESC",
    )
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM file_access_logs WHERE {where_sql}", tuple(params)))
        rows = conn.execute(
            f"""
            SELECT *
            FROM file_access_logs
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, offset),
        ).fetchall()
    return [row_to_access_log(dict(row)) for row in rows], total


def create_index_job(
    *,
    tenant_id: int,
    file_id: int | None,
    job_type: str,
    status: str,
    payload: dict[str, Any],
    actor: str,
    actor_id: int | None,
    last_error: str = "",
) -> FileSearchIndexJob:
    timestamp = now_iso()
    finished_time = timestamp if status in {"succeeded", "failed"} else None
    attempts = 1 if status in {"succeeded", "failed"} else 0
    with connect(database_target(), readonly=False) as conn:
        require_file_management_schema(conn)
        cursor = conn.execute(
            """
            INSERT INTO file_search_index_jobs (
                tenant_id, file_id, job_type, status, attempts, last_error, scheduled_time,
                finished_time, payload_json, creator, creator_id, editor, editor_id,
                create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                file_id,
                job_type,
                status,
                attempts,
                last_error,
                timestamp,
                finished_time,
                encode_json(payload),
                actor,
                actor_id,
                actor,
                actor_id,
                timestamp,
                timestamp,
            ),
        )
        job_id = inserted_id(conn, cursor, "file_search_index_jobs", timestamp, actor)
        row = conn.execute("SELECT * FROM file_search_index_jobs WHERE id = ?", (job_id,)).fetchone()
    return row_to_index_job(dict(row))


def list_index_jobs(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    file_id: int | None = None,
    status: str = "",
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> tuple[list[FileSearchIndexJob], int]:
    offset = (page - 1) * page_size
    filters = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    if file_id is not None:
        filters.append("file_id = ?")
        params.append(file_id)
    if status:
        filters.append("status = ?")
        params.append(status)
    where_sql = " AND ".join(filters)
    order_by = build_order_by(
        parse_sort_params(sort_by, sort_dir),
        allowed=INDEX_JOB_SORT_COLUMNS,
        default="create_time DESC, id DESC",
        tie_breaker="id DESC",
    )
    with connect(database_target(), readonly=True) as conn:
        require_file_management_schema(conn)
        total = count_row(conn.execute(f"SELECT COUNT(*) AS total FROM file_search_index_jobs WHERE {where_sql}", tuple(params)))
        rows = conn.execute(
            f"""
            SELECT *
            FROM file_search_index_jobs
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, offset),
        ).fetchall()
    return [row_to_index_job(dict(row)) for row in rows], total


def unset_default_profiles(conn: Any, *, provider: str, actor: str, actor_id: int | None, timestamp: str) -> None:
    conn.execute(
        """
        UPDATE file_storage_profiles
        SET is_default = 0, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
        WHERE provider = ? AND deleted = 0
        """,
        (actor, actor_id, timestamp, provider),
    )


def unset_default_preview_profiles(conn: Any, *, actor: str, actor_id: int | None, timestamp: str) -> None:
    conn.execute(
        """
        UPDATE file_preview_profiles
        SET is_default = 0, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
        WHERE deleted = 0
        """,
        (actor, actor_id, timestamp),
    )


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


def row_to_library(row: dict[str, Any]) -> FileLibrary:
    return FileLibrary(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        name=str(row.get("name") or ""),
        description=str(row.get("description") or ""),
        library_type=str(row.get("library_type") or "general"),
        visibility=str(row.get("visibility") or "tenant"),
        status=str(row.get("status") or "active"),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_folder(row: dict[str, Any]) -> FileFolder:
    return FileFolder(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        library_id=int(row["library_id"]),
        parent_id=int(row["parent_id"]) if row.get("parent_id") is not None else None,
        name=str(row.get("name") or ""),
        description=str(row.get("description") or ""),
        status=str(row.get("status") or "active"),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_file(row: dict[str, Any]) -> ManagedFile:
    return ManagedFile(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        library_id=int(row["library_id"]) if row.get("library_id") is not None else None,
        folder_id=int(row["folder_id"]) if row.get("folder_id") is not None else None,
        original_name=str(row.get("original_name") or ""),
        display_name=str(row.get("display_name") or ""),
        extension=str(row.get("extension") or ""),
        mime_type=str(row.get("mime_type") or "application/octet-stream"),
        size_bytes=int(row.get("size_bytes") or 0),
        sha256=str(row.get("sha256") or ""),
        storage_provider=str(row.get("storage_provider") or "minio"),
        storage_bucket=str(row.get("storage_bucket") or ""),
        storage_key=str(row.get("storage_key") or ""),
        status=str(row.get("status") or FILE_STATUS_AVAILABLE),
        visibility=str(row.get("visibility") or "tenant"),
        metadata=decode_json(row.get("metadata_json")),
        indexed_at=str(row["indexed_at"]) if row.get("indexed_at") is not None else None,
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_quota(row: dict[str, Any]) -> TenantStorageQuota:
    return TenantStorageQuota(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        quota_bytes=int(row.get("quota_bytes") or 0),
        max_file_size_bytes=int(row.get("max_file_size_bytes") or 0),
        allowed_mime_types=decode_json_list(row.get("allowed_mime_types_json")),
        blocked_extensions=decode_json_list(row.get("blocked_extensions_json")),
        enabled=bool(row.get("enabled")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_storage_profile(row: dict[str, Any]) -> StorageProfile:
    return StorageProfile(
        id=int(row["id"]),
        tenant_id=int(row.get("tenant_id") or 0),
        provider=str(row.get("provider") or "minio"),
        name=str(row.get("name") or ""),
        endpoint=str(row.get("endpoint") or ""),
        region=str(row.get("region") or ""),
        bucket=str(row.get("bucket") or ""),
        access_key_id=str(row.get("access_key_id") or ""),
        secret_access_key=str(row.get("secret_access_key_encrypted") or ""),
        path_style_enabled=bool(row.get("path_style_enabled")),
        tls_enabled=bool(row.get("tls_enabled")),
        is_default=bool(row.get("is_default")),
        enabled=bool(row.get("enabled")),
        extra_config=decode_json(row.get("extra_config_json")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_preview_profile(row: dict[str, Any]) -> PreviewProfile:
    return PreviewProfile(
        id=int(row["id"]),
        tenant_id=int(row.get("tenant_id") or 0),
        provider=str(row.get("provider") or "kkfileview"),
        name=str(row.get("name") or ""),
        base_url=str(row.get("base_url") or ""),
        enabled=bool(row.get("enabled")),
        is_default=bool(row.get("is_default")),
        supported_extensions=decode_json_list(row.get("supported_extensions_json")),
        config=decode_json(row.get("config_json")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_access_log(row: dict[str, Any]) -> FileAccessLog:
    return FileAccessLog(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        file_id=int(row["file_id"]) if row.get("file_id") is not None else None,
        action=str(row.get("action") or ""),
        actor_user_id=int(row["actor_user_id"]) if row.get("actor_user_id") is not None else None,
        actor_name=str(row.get("actor_name") or ""),
        client_ip=str(row.get("client_ip") or ""),
        user_agent=str(row.get("user_agent") or ""),
        result=str(row.get("result") or ""),
        detail=decode_json(row.get("detail_json")),
        create_time=str(row.get("create_time") or ""),
    )


def row_to_index_job(row: dict[str, Any]) -> FileSearchIndexJob:
    return FileSearchIndexJob(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        file_id=int(row["file_id"]) if row.get("file_id") is not None else None,
        job_type=str(row.get("job_type") or ""),
        status=str(row.get("status") or ""),
        attempts=int(row.get("attempts") or 0),
        last_error=str(row.get("last_error") or ""),
        scheduled_time=str(row.get("scheduled_time") or ""),
        finished_time=str(row["finished_time"]) if row.get("finished_time") is not None else None,
        payload=decode_json(row.get("payload_json")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def encode_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def encode_json_list(value: list[str]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item or "").strip().lower().lstrip(".")
        if text and text not in normalized:
            normalized.append(text)
    return normalized


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


def decode_json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if not value:
        return []
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload]
