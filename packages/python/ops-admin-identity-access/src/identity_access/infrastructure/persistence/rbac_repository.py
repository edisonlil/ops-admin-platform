from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from identity_access.infrastructure.persistence.common import (
    auth_database_target,
    build_menu_tree,
    connect,
    now_iso,
    require_auth_ready,
    row_to_menu,
)


def ensure_permission_definition(conn: Any, code: str) -> None:
    normalized = code.strip()
    if not normalized:
        return
    existing = conn.execute("SELECT id FROM permissions WHERE code = ?", (normalized,)).fetchone()
    if existing:
        return
    conn.execute(
        """
        INSERT INTO permissions (code, name, description)
        VALUES (?, ?, ?)
        """,
        (normalized, normalized, "Auto generated from menu management"),
    )


def rebuild_all_role_permissions(conn: Any) -> None:
    role_rows = conn.execute("SELECT id FROM roles").fetchall()
    for row in role_rows:
        role_id = int(row["id"])
        permission_rows = conn.execute(
            """
            SELECT DISTINCT p.id
            FROM permissions p
            JOIN menus m ON m.permission_code = p.code
            JOIN role_menus rm ON rm.menu_id = m.id
            WHERE rm.role_id = ? AND coalesce(m.permission_code, '') <> ''
            ORDER BY p.id
            """,
            (role_id,),
        ).fetchall()
        conn.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
        for permission_row in permission_rows:
            conn.execute(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
                """,
                (role_id, int(permission_row["id"])),
            )


def menu_tree_rows(conn: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute("SELECT * FROM menus ORDER BY sort_order, id").fetchall()]


def collect_menu_subtree(rows: list[dict[str, Any]], menu_key: str) -> list[dict[str, Any]]:
    children_by_parent: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        children_by_parent.setdefault(str(row.get("parent_key", "") or ""), []).append(row)

    collected: list[dict[str, Any]] = []

    def visit(key: str) -> None:
        current = next((row for row in rows if str(row.get("menu_key", "")) == key), None)
        if not current:
            return
        collected.append(current)
        for child in children_by_parent.get(key, []):
            visit(str(child.get("menu_key", "")))

    visit(menu_key)
    return collected


def bound_roles_for_menu_keys(conn: Any, menu_keys: list[str]) -> list[dict[str, Any]]:
    normalized = [key for key in {str(item).strip() for item in menu_keys} if key]
    if not normalized:
        return []
    placeholders = ", ".join("?" for _ in normalized)
    rows = conn.execute(
        f"""
        SELECT DISTINCT r.id, r.role_key, r.name
        FROM role_menus rm
        JOIN menus m ON m.id = rm.menu_id
        JOIN roles r ON r.id = rm.role_id
        WHERE m.menu_key IN ({placeholders})
        ORDER BY r.role_key
        """,
        tuple(normalized),
    ).fetchall()
    return [
        {"id": int(row["id"]), "key": str(row["role_key"]), "name": str(row["name"])}
        for row in rows
    ]


def ensure_menu_not_bound(conn: Any, menu_keys: list[str]) -> None:
    bound_roles = bound_roles_for_menu_keys(conn, menu_keys)
    if bound_roles:
        role_names = ", ".join(role["name"] or role["key"] for role in bound_roles)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"menu is assigned to roles: {role_names}. unbind roles before modifying or deleting it",
        )


def ensure_menu_structure_not_changed_when_bound(
    conn: Any,
    *,
    current_key: str,
    next_key: str,
    current_menu_type: str,
    next_menu_type: str,
    current_path: str,
    next_path: str,
    current_parent_key: str,
    next_parent_key: str,
) -> None:
    bound_roles = bound_roles_for_menu_keys(conn, [current_key])
    if not bound_roles:
        return

    if (
        current_menu_type != next_menu_type
        or current_path != next_path
        or current_parent_key != next_parent_key
    ):
        role_names = ", ".join(role["name"] or role["key"] for role in bound_roles)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"menu structure is assigned to roles: {role_names}. unbind roles before changing menu type, path, or parent",
        )


def user_access_payload(
    user_id: int,
    is_superuser: bool,
    *,
    tenant_id: int | None = None,
    auth_scope: str | None = None,
    is_tenant_admin: bool = False,
) -> dict[str, Any]:
    if not user_id:
        return {"roles": [], "permissions": [], "menus": []}
    effective_scope = (auth_scope or ("platform" if is_superuser else "tenant")).strip().lower()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        role_rows = conn.execute(
            """
            SELECT DISTINCT r.role_key, r.name, r.description, r.is_system, r.role_scope
            FROM roles r
            JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = ?
              AND r.role_scope = ?
            ORDER BY r.role_key
            """,
            (user_id, "platform" if effective_scope == "platform" else "tenant"),
        ).fetchall()
        if effective_scope == "platform" and is_superuser:
            permission_rows = conn.execute("SELECT code FROM permissions ORDER BY code").fetchall()
            menu_rows = conn.execute(
                """
                SELECT *
                FROM menus
                WHERE menu_scope = ?
                ORDER BY sort_order, id
                """,
                ("platform",),
            ).fetchall()
        else:
            permission_rows = conn.execute(
                """
                SELECT DISTINCT p.code
                FROM permissions p
                JOIN role_permissions rp ON rp.permission_id = p.id
                JOIN roles r ON r.id = rp.role_id
                JOIN user_roles ur ON ur.role_id = rp.role_id
                WHERE ur.user_id = ?
                  AND r.role_scope = ?
                ORDER BY p.code
                """,
                (user_id, "tenant"),
            ).fetchall()
            menu_rows = conn.execute(
                """
                SELECT DISTINCT m.*
                FROM menus m
                JOIN role_menus rm ON rm.menu_id = m.id
                JOIN roles r ON r.id = rm.role_id
                JOIN user_roles ur ON ur.role_id = rm.role_id
                JOIN tenant_menu_overrides tmo ON tmo.menu_key = m.menu_key
                WHERE ur.user_id = ?
                  AND r.role_scope = ?
                  AND m.menu_scope = ?
                  AND tmo.tenant_id = ?
                  AND tmo.is_enabled = TRUE
                ORDER BY m.sort_order, m.id
                """,
                (user_id, "tenant", "tenant", int(tenant_id or 0)),
            ).fetchall()
    return {
        "roles": [
            {
                "key": str(dict(row)["role_key"]),
                "name": str(dict(row)["name"]),
                "description": str(dict(row).get("description", "") or ""),
                "is_system": bool(dict(row).get("is_system", False)),
                "role_scope": str(dict(row).get("role_scope", "") or "platform"),
            }
            for row in role_rows
            if effective_scope == "platform" or str(dict(row).get("role_scope", "") or "platform") == "tenant"
        ],
        "permissions": [str(row["code"]) for row in permission_rows],
        "menus": build_menu_tree([dict(row) for row in menu_rows]),
    }


def list_roles() -> list[dict[str, Any]]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        role_rows = conn.execute("SELECT * FROM roles ORDER BY role_key").fetchall()
        permission_rows = conn.execute(
            """
            SELECT rp.role_id, p.code, p.name
            FROM role_permissions rp
            JOIN permissions p ON p.id = rp.permission_id
            ORDER BY p.code
            """
        ).fetchall()
        menu_rows = conn.execute(
            """
            SELECT rm.role_id, m.menu_key, m.label
            FROM role_menus rm
            JOIN menus m ON m.id = rm.menu_id
            ORDER BY m.sort_order, m.id
            """
        ).fetchall()
    permissions_by_role: dict[int, list[dict[str, str]]] = {}
    for row in permission_rows:
        permissions_by_role.setdefault(int(row["role_id"]), []).append(
            {"code": str(row["code"]), "name": str(row["name"])}
        )
    menus_by_role: dict[int, list[dict[str, str]]] = {}
    for row in menu_rows:
        menus_by_role.setdefault(int(row["role_id"]), []).append(
            {"key": str(row["menu_key"]), "label": str(row["label"])}
        )
    return [
        {
            "id": int(dict(row)["id"]),
            "key": str(dict(row)["role_key"]),
            "name": str(dict(row)["name"]),
            "description": str(dict(row).get("description", "") or ""),
            "is_system": bool(dict(row).get("is_system", False)),
            "role_scope": str(dict(row).get("role_scope", "") or "platform"),
            "permissions": permissions_by_role.get(int(dict(row)["id"]), []),
            "menus": menus_by_role.get(int(dict(row)["id"]), []),
            "create_time": str(dict(row).get("create_time", "") or ""),
            "update_time": str(dict(row).get("update_time", "") or ""),
        }
        for row in role_rows
    ]


def resolve_role_menu_selection(conn: Any, menu_keys: list[str], *, role_scope: str = "platform") -> tuple[list[dict[str, Any]], list[int]]:
    requested_keys = [str(key).strip() for key in menu_keys if str(key).strip()]
    menu_rows = conn.execute(
        """
        SELECT id, menu_key, parent_key, permission_code
        FROM menus
        WHERE menu_scope = ?
        ORDER BY sort_order, id
        """,
        (role_scope,),
    ).fetchall()
    menu_by_key = {str(row["menu_key"]): dict(row) for row in menu_rows}
    invalid_keys = [key for key in requested_keys if key not in menu_by_key]
    if invalid_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown menu keys: {', '.join(invalid_keys)}",
        )

    selected_keys = set(requested_keys)
    for key in requested_keys:
        parent_key = str(menu_by_key[key].get("parent_key", "") or "")
        while parent_key and parent_key in menu_by_key:
            selected_keys.add(parent_key)
            parent_key = str(menu_by_key[parent_key].get("parent_key", "") or "")

    selected_menus = sorted((menu_by_key[key] for key in selected_keys), key=lambda item: int(item["id"]))
    permission_codes = sorted(
        {
            str(menu.get("permission_code", "") or "")
            for menu in selected_menus
            if str(menu.get("permission_code", "") or "").strip()
        }
    )
    if not permission_codes:
        return selected_menus, []
    placeholders = ", ".join("?" for _ in permission_codes)
    permission_rows = conn.execute(
        f"SELECT id FROM permissions WHERE code IN ({placeholders}) ORDER BY code",
        tuple(permission_codes),
    ).fetchall()
    return selected_menus, [int(row["id"]) for row in permission_rows]


def sync_role_access(conn: Any, role_id: int, menu_keys: list[str]) -> None:
    role_row = conn.execute("SELECT role_scope FROM roles WHERE id = ?", (role_id,)).fetchone()
    role_scope = str(role_row["role_scope"] if role_row else "platform" or "platform")
    selected_menus, permission_ids = resolve_role_menu_selection(conn, menu_keys, role_scope=role_scope)
    conn.execute("DELETE FROM role_menus WHERE role_id = ?", (role_id,))
    for menu in selected_menus:
        conn.execute(
            """
            INSERT INTO role_menus (role_id, menu_id)
            VALUES (?, ?)
            """,
            (role_id, int(menu["id"])),
        )

    conn.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
    for permission_id in permission_ids:
        conn.execute(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            VALUES (?, ?)
            """,
            (role_id, permission_id),
        )


def create_role(
    *,
    role_key: str,
    name: str,
    description: str = "",
    role_scope: str = "platform",
    menu_keys: list[str] | None = None,
) -> dict[str, Any]:
    normalized_key = role_key.strip()
    normalized_scope = role_scope.strip() or "platform"
    if normalized_scope not in {"platform", "tenant"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role scope must be platform or tenant")
    now = now_iso()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        existing = conn.execute("SELECT id FROM roles WHERE role_key = ?", (normalized_key,)).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="role key already exists")

        cursor = conn.execute(
            """
            INSERT INTO roles (role_key, name, description, is_system, role_scope, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (normalized_key, name.strip(), description.strip(), False, normalized_scope, now, now),
        )
        role_id = int(getattr(cursor, "lastrowid", 0) or 0)
        if not role_id:
            row = conn.execute("SELECT id FROM roles WHERE role_key = ?", (normalized_key,)).fetchone()
            role_id = int(row["id"])
        sync_role_access(conn, role_id, list(menu_keys or []))

    for role in list_roles():
        if int(role["id"]) == role_id:
            return role
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="role not found")


def update_role(
    role_id: int,
    *,
    role_key: str,
    name: str,
    description: str = "",
    menu_keys: list[str] | None = None,
) -> dict[str, Any]:
    normalized_key = role_key.strip()
    now = now_iso()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        role_row = conn.execute(
            "SELECT id, role_key, is_system FROM roles WHERE id = ?",
            (role_id,),
        ).fetchone()
        if not role_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="role not found")

        current_key = str(role_row["role_key"])
        is_system = bool(role_row["is_system"])
        if is_system and normalized_key != current_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="system role key cannot be changed")

        existing = conn.execute(
            "SELECT id FROM roles WHERE role_key = ? AND id <> ?",
            (normalized_key, role_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="role key already exists")

        conn.execute(
            """
            UPDATE roles
            SET role_key = ?, name = ?, description = ?, update_time = ?
            WHERE id = ?
            """,
            (normalized_key, name.strip(), description.strip(), now, role_id),
        )
        sync_role_access(conn, role_id, list(menu_keys or []))

    for role in list_roles():
        if int(role["id"]) == role_id:
            return role
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="role not found")


def update_role_menus(role_id: int, menu_keys: list[str]) -> dict[str, Any]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        role_row = conn.execute("SELECT id FROM roles WHERE id = ?", (role_id,)).fetchone()
        if not role_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="role not found")
        sync_role_access(conn, role_id, menu_keys)

    for role in list_roles():
        if int(role["id"]) == role_id:
            return role
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="role not found")


def delete_role(role_id: int) -> dict[str, Any]:
    roles = list_roles()
    role = next((item for item in roles if int(item["id"]) == role_id), None)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="role not found")
    if bool(role.get("is_system")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="system role cannot be deleted")

    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        conn.execute("DELETE FROM user_roles WHERE role_id = ?", (role_id,))
        conn.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
        conn.execute("DELETE FROM role_menus WHERE role_id = ?", (role_id,))
        conn.execute("DELETE FROM roles WHERE id = ?", (role_id,))
    return role


def validate_menu_payload(
    conn: Any,
    *,
    menu_key: str,
    label: str,
    menu_type: str,
    path: str,
    route_name: str,
    component: str,
    parent_key: str,
    menu_id: int | None = None,
) -> dict[str, Any]:
    normalized_key = menu_key.strip()
    normalized_label = label.strip()
    normalized_type = menu_type.strip().lower()
    normalized_path = path.strip()
    normalized_route_name = route_name.strip() or normalized_key
    normalized_component = component.strip()
    normalized_parent_key = parent_key.strip()

    if not normalized_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="menu key is required")
    if not normalized_label:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="menu label is required")
    if normalized_type not in {"directory", "page", "action"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="menu type must be directory, page or action")
    if normalized_type == "page":
        if not normalized_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page menu path is required")
        if not normalized_component:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page menu component is required")
    if normalized_type == "action":
        normalized_path = ""
        normalized_route_name = normalized_key
        normalized_component = ""
        if not normalized_parent_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="action menu parent is required")

    existing = conn.execute(
        "SELECT id FROM menus WHERE menu_key = ? AND (? IS NULL OR id <> ?)",
        (normalized_key, menu_id, menu_id),
    ).fetchone()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="menu key already exists")

    if normalized_parent_key:
        parent_row = conn.execute(
            "SELECT id, menu_key, menu_type FROM menus WHERE menu_key = ?",
            (normalized_parent_key,),
        ).fetchone()
        if not parent_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="parent menu not found")
        parent_type = str(parent_row["menu_type"] or "page")
        if normalized_type == "action":
            if parent_type != "page":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="action parent menu must be a page")
        elif parent_type != "directory":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="parent menu must be a directory")
        if menu_id is not None and int(parent_row["id"]) == menu_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="menu cannot be its own parent")
        if menu_id is not None:
            rows = menu_tree_rows(conn)
            subtree = collect_menu_subtree(rows, normalized_key)
            subtree_keys = {str(row.get("menu_key", "")) for row in subtree}
            if normalized_parent_key in subtree_keys:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="menu cannot move under its descendant")

    if menu_id is not None and normalized_type in {"page", "action"}:
        child_row = conn.execute("SELECT id FROM menus WHERE parent_key = ? LIMIT 1", (normalized_key,)).fetchone()
        if child_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="menu with children cannot become a page or action")

    return {
        "menu_key": normalized_key,
        "label": normalized_label,
        "menu_type": normalized_type,
        "path": normalized_path,
        "route_name": normalized_route_name,
        "component": normalized_component,
        "parent_key": normalized_parent_key,
    }


def create_menu(
    *,
    menu_key: str,
    label: str,
    menu_type: str,
    path: str = "",
    route_name: str = "",
    component: str = "",
    icon: str = "",
    parent_key: str = "",
    permission_code: str = "",
    sort_order: int = 0,
    is_visible: bool = True,
) -> dict[str, Any]:
    now = now_iso()
    normalized_permission = permission_code.strip()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        payload = validate_menu_payload(
            conn,
            menu_key=menu_key,
            label=label,
            menu_type=menu_type,
            path=path,
            route_name=route_name,
            component=component,
            parent_key=parent_key,
        )
        ensure_permission_definition(conn, normalized_permission)
        cursor = conn.execute(
            """
            INSERT INTO menus (
                menu_key, menu_scope, label, menu_type, path, route_name, component, icon,
                parent_key, permission_code, sort_order, is_visible
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["menu_key"],
                "platform",
                payload["label"],
                payload["menu_type"],
                payload["path"],
                payload["route_name"],
                payload["component"],
                icon.strip(),
                payload["parent_key"],
                normalized_permission,
                int(sort_order),
                bool(is_visible),
            ),
        )
        menu_id = int(getattr(cursor, "lastrowid", 0) or 0)
        if not menu_id:
            row = conn.execute("SELECT id FROM menus WHERE menu_key = ?", (payload["menu_key"],)).fetchone()
            menu_id = int(row["id"])
        rebuild_all_role_permissions(conn)

    menu = next((item for item in list_menus() if int(item["id"]) == menu_id), None)
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="menu not found")
    return menu


def update_menu(
    menu_id: int,
    *,
    menu_key: str,
    label: str,
    menu_type: str,
    path: str = "",
    route_name: str = "",
    component: str = "",
    icon: str = "",
    parent_key: str = "",
    permission_code: str = "",
    sort_order: int = 0,
    is_visible: bool = True,
) -> dict[str, Any]:
    now = now_iso()
    normalized_permission = permission_code.strip()
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        current = conn.execute(
            """
            SELECT id, menu_key, menu_type, path, parent_key
            FROM menus
            WHERE id = ?
            """,
            (menu_id,),
        ).fetchone()
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="menu not found")
        rows = menu_tree_rows(conn)
        payload = validate_menu_payload(
            conn,
            menu_key=menu_key,
            label=label,
            menu_type=menu_type,
            path=path,
            route_name=route_name,
            component=component,
            parent_key=parent_key,
            menu_id=menu_id,
        )
        current_key = str(current["menu_key"])
        ensure_menu_structure_not_changed_when_bound(
            conn,
            current_key=current_key,
            next_key=payload["menu_key"],
            current_menu_type=str(current["menu_type"] or "page"),
            next_menu_type=payload["menu_type"],
            current_path=str(current["path"] or ""),
            next_path=payload["path"],
            current_parent_key=str(current["parent_key"] or ""),
            next_parent_key=payload["parent_key"],
        )
        ensure_permission_definition(conn, normalized_permission)
        conn.execute(
            """
            UPDATE menus
            SET menu_key = ?, label = ?, menu_type = ?, path = ?, route_name = ?,
                component = ?, icon = ?, parent_key = ?, permission_code = ?,
                sort_order = ?, is_visible = ?
            WHERE id = ?
            """,
            (
                payload["menu_key"],
                payload["label"],
                payload["menu_type"],
                payload["path"],
                payload["route_name"],
                payload["component"],
                icon.strip(),
                payload["parent_key"],
                normalized_permission,
                int(sort_order),
                bool(is_visible),
                menu_id,
            ),
        )
        if payload["menu_key"] != current_key:
            conn.execute(
                """
                UPDATE menus
                SET parent_key = ?
                WHERE parent_key = ?
                """,
                (payload["menu_key"], current_key),
            )
        conn.execute("UPDATE roles SET update_time = ? WHERE id IN (SELECT role_id FROM role_menus)", (now,))
        rebuild_all_role_permissions(conn)

    menu = next((item for item in list_menus() if int(item["id"]) == menu_id), None)
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="menu not found")
    return menu


def delete_menu(menu_id: int) -> dict[str, Any]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        current = conn.execute("SELECT * FROM menus WHERE id = ?", (menu_id,)).fetchone()
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="menu not found")
        rows = menu_tree_rows(conn)
        subtree = collect_menu_subtree(rows, str(current["menu_key"]))
        ensure_menu_not_bound(conn, [str(row.get("menu_key", "")) for row in subtree])
        subtree_ids = [int(row["id"]) for row in subtree]
        placeholders = ", ".join("?" for _ in subtree_ids)
        conn.execute(f"DELETE FROM role_menus WHERE menu_id IN ({placeholders})", tuple(subtree_ids))
        conn.execute(f"DELETE FROM menus WHERE id IN ({placeholders})", tuple(subtree_ids))
        rebuild_all_role_permissions(conn)
    return row_to_menu(dict(current))


def list_permissions() -> list[dict[str, str]]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        rows = conn.execute("SELECT * FROM permissions ORDER BY code").fetchall()
    return [
        {
            "code": str(row["code"]),
            "name": str(row["name"]),
            "description": str(dict(row).get("description", "") or ""),
        }
        for row in rows
    ]


def list_menus() -> list[dict[str, Any]]:
    with connect(auth_database_target(), readonly=False) as conn:
        require_auth_ready(conn)
        rows = conn.execute("SELECT * FROM menus ORDER BY sort_order, id").fetchall()
        role_rows = conn.execute(
            """
            SELECT rm.menu_id, r.id AS role_id, r.role_key, r.name
            FROM role_menus rm
            JOIN roles r ON r.id = rm.role_id
            ORDER BY r.role_key
            """
        ).fetchall()
    roles_by_menu: dict[int, list[dict[str, Any]]] = {}
    for row in role_rows:
        roles_by_menu.setdefault(int(row["menu_id"]), []).append(
            {"id": int(row["role_id"]), "key": str(row["role_key"]), "name": str(row["name"])}
        )
    items: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_menu(dict(row))
        item["bound_roles"] = roles_by_menu.get(int(row["id"]), [])
        item["bound_role_count"] = len(item["bound_roles"])
        items.append(item)
    return items
