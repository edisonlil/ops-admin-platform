from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from organization.domain.exceptions import OrganizationDomainError
from organization.domain.models import Department, STATUS_ACTIVE, STATUS_DISABLED
from organization.infrastructure.persistence.bootstrap import require_organization_schema
from system.application.database import connect, resolve_database_url, resolve_db_path


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def execute_many(conn: Any, sql: str, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    if hasattr(conn, "executemany"):
        conn.executemany(sql, rows)
        return
    for row in rows:
        conn.execute(sql, row)


def list_departments(*, tenant_id: int, include_disabled: bool = False) -> list[Department]:
    where = ["tenant_id = ?", "deleted = 0"]
    params: list[Any] = [tenant_id]
    if not include_disabled:
        where.append("status = ?")
        params.append(STATUS_ACTIVE)
    with connect(database_target(), readonly=True) as conn:
        require_organization_schema(conn)
        rows = conn.execute(
            f"""
            SELECT *
            FROM departments
            WHERE {" AND ".join(where)}
            ORDER BY sort_order ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
    return [row_to_department(dict(row)) for row in rows]


def get_department(*, tenant_id: int, department_id: int) -> Department | None:
    with connect(database_target(), readonly=True) as conn:
        require_organization_schema(conn)
        row = conn.execute(
            "SELECT * FROM departments WHERE tenant_id = ? AND id = ? AND deleted = 0",
            (tenant_id, department_id),
        ).fetchone()
    return row_to_department(dict(row)) if row else None


def save_department(*, tenant_id: int, payload: dict[str, Any], actor: str, actor_id: int | None) -> Department:
    department_id = int(payload.get("id") or 0)
    code = str(payload.get("code") or "").strip()
    name = str(payload.get("name") or "").strip()
    status_value = normalize_status(payload.get("status"))
    parent_id = int(payload.get("parent_id") or 0) or None
    manager_user_id = int(payload.get("manager_user_id") or 0) or None
    if not code:
        raise OrganizationDomainError("department code is required")
    if not name:
        raise OrganizationDomainError("department name is required")
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_organization_schema(conn)
        validate_department_parent(conn, tenant_id=tenant_id, department_id=department_id, parent_id=parent_id)
        try:
            if department_id:
                conn.execute(
                    """
                    UPDATE departments
                    SET parent_id = ?, code = ?, name = ?, manager_user_id = ?, base_location = ?, region = ?,
                        status = ?, sort_order = ?, editor = ?, editor_id = ?, update_time = ?,
                        lock_version = lock_version + 1
                    WHERE tenant_id = ? AND id = ? AND deleted = 0
                    """,
                    (
                        parent_id,
                        code,
                        name,
                        manager_user_id,
                        str(payload.get("base_location") or "").strip(),
                        str(payload.get("region") or "").strip(),
                        status_value,
                        int(payload.get("sort_order") or 0),
                        actor,
                        actor_id,
                        timestamp,
                        tenant_id,
                        department_id,
                    ),
                )
                saved_id = department_id
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO departments (
                        tenant_id, parent_id, code, name, manager_user_id, base_location, region,
                        status, sort_order, creator, creator_id, editor, editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        parent_id,
                        code,
                        name,
                        manager_user_id,
                        str(payload.get("base_location") or "").strip(),
                        str(payload.get("region") or "").strip(),
                        status_value,
                        int(payload.get("sort_order") or 0),
                        actor,
                        actor_id,
                        actor,
                        actor_id,
                        timestamp,
                        timestamp,
                    ),
                )
                saved_id = inserted_id(conn, cursor, "departments", timestamp, actor)
        except sqlite3.IntegrityError as exc:
            raise_unique_constraint_error(exc)
    item = get_department(tenant_id=tenant_id, department_id=saved_id)
    if item is None:
        raise RuntimeError("department save failed")
    return item


def delete_department(*, tenant_id: int, department_id: int, actor: str, actor_id: int | None) -> Department | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_organization_schema(conn)
        existing = conn.execute(
            "SELECT * FROM departments WHERE tenant_id = ? AND id = ? AND deleted = 0",
            (tenant_id, department_id),
        ).fetchone()
        if not existing:
            return None
        child = conn.execute(
            "SELECT id FROM departments WHERE tenant_id = ? AND parent_id = ? AND deleted = 0 LIMIT 1",
            (tenant_id, department_id),
        ).fetchone()
        if child:
            raise OrganizationDomainError("department has child departments")
        member = conn.execute(
            "SELECT id FROM user_department_memberships WHERE tenant_id = ? AND department_id = ? AND deleted = 0 LIMIT 1",
            (tenant_id, department_id),
        ).fetchone()
        if member:
            raise OrganizationDomainError("department has assigned users")
        conn.execute(
            """
            UPDATE departments
            SET code = ?, deleted = 1, status = ?, editor = ?, editor_id = ?, update_time = ?,
                lock_version = lock_version + 1
            WHERE tenant_id = ? AND id = ?
            """,
            (f"__deleted__{department_id}", STATUS_DISABLED, actor, actor_id, timestamp, tenant_id, department_id),
        )
    return row_to_department(dict(existing))


def set_user_departments(
    *,
    tenant_id: int,
    user_id: int,
    department_ids: list[int],
    primary_department_id: int | None,
    actor: str,
    actor_id: int | None,
) -> list[dict[str, Any]]:
    normalized_ids = []
    seen: set[int] = set()
    for value in department_ids:
        department_id = int(value or 0)
        if department_id and department_id not in seen:
            normalized_ids.append(department_id)
            seen.add(department_id)
    if primary_department_id and primary_department_id not in seen:
        normalized_ids.insert(0, primary_department_id)
    elif normalized_ids and not primary_department_id:
        primary_department_id = normalized_ids[0]
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_organization_schema(conn)
        for department_id in normalized_ids:
            department = conn.execute(
                "SELECT id FROM departments WHERE tenant_id = ? AND id = ? AND deleted = 0 AND status = ?",
                (tenant_id, department_id, STATUS_ACTIVE),
            ).fetchone()
            if not department:
                raise OrganizationDomainError(f"department not found: {department_id}")
        current_rows = conn.execute(
            """
            SELECT id, department_id
            FROM user_department_memberships
            WHERE tenant_id = ? AND user_id = ? AND deleted = 0
            """,
            (tenant_id, user_id),
        ).fetchall()
        target_ids = set(normalized_ids)
        current_by_department = {int(row["department_id"]): int(row["id"]) for row in current_rows}
        removed_ids = [department_id for department_id in current_by_department if department_id not in target_ids]
        if removed_ids:
            placeholders = ", ".join("?" for _ in removed_ids)
            conn.execute(
                f"""
                UPDATE user_department_memberships
                SET deleted = 1,
                    active_marker = NULL,
                    is_primary = 0,
                    editor = ?,
                    editor_id = ?,
                    update_time = ?,
                    lock_version = lock_version + 1
                WHERE tenant_id = ?
                  AND user_id = ?
                  AND deleted = 0
                  AND department_id IN ({placeholders})
                """,
                (actor, actor_id, timestamp, tenant_id, user_id, *removed_ids),
            )
        for department_id in normalized_ids:
            is_primary = int(department_id) == int(primary_department_id or 0)
            existing_id = current_by_department.get(department_id)
            if existing_id:
                conn.execute(
                    """
                    UPDATE user_department_memberships
                    SET is_primary = ?,
                        editor = ?,
                        editor_id = ?,
                        update_time = ?,
                        lock_version = lock_version + 1
                    WHERE id = ?
                    """,
                    (is_primary, actor, actor_id, timestamp, existing_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO user_department_memberships (
                        tenant_id, user_id, department_id, is_primary, active_marker,
                        creator, creator_id, editor, editor_id, create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
                    """,
                    (tenant_id, user_id, department_id, is_primary, actor, actor_id, actor, actor_id, timestamp, timestamp),
                )
    return user_departments(tenant_id=tenant_id, user_id=user_id)


def set_users_departments_batch(
    rows: list[dict[str, Any]],
    *,
    actor: str,
    actor_id: int | None,
) -> None:
    normalized_rows: list[dict[str, Any]] = []
    department_keys: set[tuple[int, int]] = set()
    for row in rows:
        tenant_id = int(row.get("tenant_id") or 0)
        user_id = int(row.get("user_id") or 0)
        if not tenant_id or not user_id:
            continue
        department_ids: list[int] = []
        seen: set[int] = set()
        for value in list(row.get("department_ids") or []):
            department_id = int(value or 0)
            if department_id and department_id not in seen:
                department_ids.append(department_id)
                seen.add(department_id)
                department_keys.add((tenant_id, department_id))
        primary_department_id = int(row.get("primary_department_id") or 0) or None
        if primary_department_id and primary_department_id not in seen:
            department_ids.insert(0, primary_department_id)
            department_keys.add((tenant_id, primary_department_id))
        elif department_ids and not primary_department_id:
            primary_department_id = department_ids[0]
        normalized_rows.append(
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "department_ids": department_ids,
                "primary_department_id": primary_department_id,
            }
        )
    if not normalized_rows:
        return

    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_organization_schema(conn)
        if department_keys:
            tenant_ids = sorted({tenant_id for tenant_id, _department_id in department_keys})
            department_ids = sorted({department_id for _tenant_id, department_id in department_keys})
            tenant_placeholders = ", ".join("?" for _ in tenant_ids)
            department_placeholders = ", ".join("?" for _ in department_ids)
            department_rows = conn.execute(
                f"""
                SELECT tenant_id, id
                FROM departments
                WHERE tenant_id IN ({tenant_placeholders})
                  AND id IN ({department_placeholders})
                  AND deleted = 0
                  AND status = ?
                """,
                (*tenant_ids, *department_ids, STATUS_ACTIVE),
            ).fetchall()
            existing_departments = {(int(row["tenant_id"]), int(row["id"])) for row in department_rows}
            missing = sorted(department_keys - existing_departments)
            if missing:
                tenant_id, department_id = missing[0]
                raise OrganizationDomainError(f"department not found: {tenant_id}/{department_id}")

        insert_rows: list[tuple[Any, ...]] = []
        for row in normalized_rows:
            tenant_id = int(row["tenant_id"])
            user_id = int(row["user_id"])
            for department_id in list(row.get("department_ids") or []):
                insert_rows.append(
                    (
                        tenant_id,
                        user_id,
                        int(department_id),
                        int(department_id) == int(row.get("primary_department_id") or 0),
                        actor,
                        actor_id,
                        actor,
                        actor_id,
                        timestamp,
                        timestamp,
                    )
                )
        execute_many(
            conn,
            """
            INSERT INTO user_department_memberships (
                tenant_id, user_id, department_id, is_primary, active_marker,
                creator, creator_id, editor, editor_id, create_time, update_time
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows,
        )


def user_departments(*, tenant_id: int, user_id: int) -> list[dict[str, Any]]:
    return users_departments(tenant_id=tenant_id, user_ids=[user_id]).get(int(user_id), [])


def users_departments(*, tenant_id: int, user_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    normalized_ids: list[int] = []
    seen: set[int] = set()
    for value in user_ids:
        user_id = int(value or 0)
        if user_id and user_id not in seen:
            normalized_ids.append(user_id)
            seen.add(user_id)
    if not normalized_ids:
        return {}
    placeholders = ", ".join("?" for _ in normalized_ids)
    with connect(database_target(), readonly=True) as conn:
        require_organization_schema(conn)
        rows = conn.execute(
            f"""
            SELECT udm.*, d.code, d.name, d.parent_id, d.base_location, d.region
            FROM user_department_memberships udm
            JOIN departments d ON d.id = udm.department_id AND d.tenant_id = udm.tenant_id
            WHERE udm.tenant_id = ? AND udm.user_id IN ({placeholders}) AND udm.deleted = 0 AND d.deleted = 0
            ORDER BY udm.user_id ASC, udm.is_primary DESC, d.sort_order ASC, d.id ASC
            """,
            (tenant_id, *normalized_ids),
        ).fetchall()
    departments_by_user = {user_id: [] for user_id in normalized_ids}
    for row in rows:
        departments_by_user.setdefault(int(row["user_id"]), []).append(row_to_user_department(dict(row)))
    return departments_by_user


def row_to_user_department(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["department_id"]),
        "department_id": int(row["department_id"]),
        "tenant_id": int(row["tenant_id"]),
        "code": str(row["code"]),
        "name": str(row["name"]),
        "parent_id": int(row["parent_id"]) if row["parent_id"] not in (None, "") else None,
        "base_location": str(row["base_location"] or ""),
        "region": str(row["region"] or ""),
        "is_primary": bool(row["is_primary"]),
    }


def validate_department_parent(conn: Any, *, tenant_id: int, department_id: int, parent_id: int | None) -> None:
    if not parent_id:
        return
    if department_id and parent_id == department_id:
        raise OrganizationDomainError("部门不能作为自己的上级部门")
    parent = conn.execute(
        "SELECT id, parent_id FROM departments WHERE tenant_id = ? AND id = ? AND deleted = 0",
        (tenant_id, parent_id),
    ).fetchone()
    if not parent:
        raise OrganizationDomainError("上级部门不存在")
    if department_id:
        current_parent_id = int(parent_id)
        visited: set[int] = set()
        while current_parent_id:
            if current_parent_id == department_id:
                raise OrganizationDomainError("部门不能移动到自己的下级部门")
            if current_parent_id in visited:
                raise OrganizationDomainError("部门层级存在循环")
            visited.add(current_parent_id)
            row = conn.execute(
                "SELECT parent_id FROM departments WHERE tenant_id = ? AND id = ? AND deleted = 0",
                (tenant_id, current_parent_id),
            ).fetchone()
            if not row:
                break
            current_parent_id = int(row["parent_id"] or 0)


def row_to_department(row: dict[str, Any]) -> Department:
    return Department(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        parent_id=int(row["parent_id"]) if row.get("parent_id") not in (None, "") else None,
        code=str(row.get("code") or ""),
        name=str(row.get("name") or ""),
        manager_user_id=int(row["manager_user_id"]) if row.get("manager_user_id") not in (None, "") else None,
        base_location=str(row.get("base_location") or ""),
        region=str(row.get("region") or ""),
        status=str(row.get("status") or STATUS_ACTIVE),
        sort_order=int(row.get("sort_order") or 0),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def normalize_status(value: Any) -> str:
    status_value = str(value or STATUS_ACTIVE).strip() or STATUS_ACTIVE
    return status_value if status_value in {STATUS_ACTIVE, STATUS_DISABLED} else STATUS_ACTIVE


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


def raise_unique_constraint_error(exc: Exception) -> None:
    message = str(exc).lower()
    if "departments" in message and ("unique" in message or "duplicate" in message):
        raise OrganizationDomainError("department code already exists") from exc
    raise exc
