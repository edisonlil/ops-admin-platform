from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from system.infrastructure.persistence.dialect import apply_sql_script, backend_name, ddl_filename, split_sql_statements


PERSISTENCE_DIR = Path(__file__).resolve().parent


def ensure_identity_schema(conn: Any) -> None:
    apply_sql_script(conn, PERSISTENCE_DIR / ddl_filename(conn))


def ensure_identity_seed(conn: Any) -> None:
    if backend_name(conn) == "mysql":
        apply_mysql_identity_seed(conn, PERSISTENCE_DIR / "seed.sql")
        return
    apply_sql_script(conn, PERSISTENCE_DIR / "seed.sql")


def apply_mysql_identity_seed(conn: Any, path: Path) -> None:
    permission_rows: list[tuple[Any, ...]] = []
    menu_rows_by_columns: dict[tuple[str, ...], list[tuple[Any, ...]]] = {}

    def flush() -> None:
        nonlocal permission_rows, menu_rows_by_columns
        if permission_rows:
            _executemany(
                conn,
                """
                INSERT IGNORE INTO permissions (code, name, description)
                VALUES (?, ?, ?)
                """,
                permission_rows,
            )
            permission_rows = []
        for columns, rows in menu_rows_by_columns.items():
            placeholders = ", ".join("?" for _ in columns)
            _executemany(
                conn,
                f"""
                INSERT IGNORE INTO menus ({", ".join(columns)})
                VALUES ({placeholders})
                """,
                rows,
            )
        menu_rows_by_columns = {}

    sql = path.read_text(encoding="utf-8-sig")
    for statement in split_sql_statements(sql):
        parsed = _parse_insert_select_if_missing(statement)
        if parsed:
            table_name, columns, values = parsed
            if table_name == "permissions" and columns == ("code", "name", "description"):
                permission_rows.append(values)
                continue
            if table_name == "menus":
                menu_rows_by_columns.setdefault(columns, []).append(values)
                continue

        flush()
        conn.execute(statement)
    flush()


def _executemany(conn: Any, sql: str, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    if hasattr(conn, "executemany"):
        conn.executemany(sql, rows)
        return
    for row in rows:
        conn.execute(sql, row)


def _parse_insert_select_if_missing(statement: str) -> tuple[str, tuple[str, ...], tuple[Any, ...]] | None:
    match = re.match(
        r"INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*SELECT\s+(.+?)\s+WHERE\s+NOT\s+EXISTS\s*\(",
        statement,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    table_name = match.group(1)
    columns = tuple(column.strip() for column in match.group(2).split(","))
    values = tuple(_parse_sql_value(token) for token in _split_sql_values(match.group(3)))
    if len(columns) != len(values):
        return None
    return table_name, columns, values


def _split_sql_values(values_sql: str) -> list[str]:
    values: list[str] = []
    current: list[str] = []
    in_string = False
    index = 0
    while index < len(values_sql):
        char = values_sql[index]
        if char == "'":
            current.append(char)
            if in_string and index + 1 < len(values_sql) and values_sql[index + 1] == "'":
                current.append(values_sql[index + 1])
                index += 2
                continue
            in_string = not in_string
            index += 1
            continue
        if char == "," and not in_string:
            values.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    if current:
        values.append("".join(current).strip())
    return values


def _parse_sql_value(token: str) -> Any:
    text = token.strip()
    upper = text.upper()
    if upper == "TRUE":
        return True
    if upper == "FALSE":
        return False
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1].replace("''", "'")
    try:
        return int(text)
    except ValueError:
        return text
