from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sqlglot
from sqlglot import exp

from system.application.data_access import DataAccessPredicate, ResourceDescriptor, normalized_identifier


class SQLDataAccessInjectionError(ValueError):
    pass


@dataclass(frozen=True)
class SQLDataAccessInjectionRequest:
    sql: str
    params: tuple[Any, ...]
    resource: ResourceDescriptor
    predicate: DataAccessPredicate
    dialect: str = "sqlite"
    source_table: str = ""
    source_alias: str = ""


def inject_data_access_into_select(request: SQLDataAccessInjectionRequest) -> tuple[str, tuple[Any, ...]]:
    sql = request.sql.strip()
    if not sql:
        raise SQLDataAccessInjectionError("SQL 不能为空")
    try:
        expressions = sqlglot.parse(sql, read=sqlglot_dialect(request.dialect))
    except Exception as exc:
        raise SQLDataAccessInjectionError(f"SQL 解析失败: {exc}") from exc
    expressions = [item for item in expressions if item is not None]
    if len(expressions) != 1:
        raise SQLDataAccessInjectionError("仅支持单条 SELECT 查询")
    expression = expressions[0]
    ensure_supported_select(expression)
    target = resolve_target_table(expression, source_table=request.source_table, source_alias=request.source_alias)
    clauses, scope_params = request.predicate.to_sql_clauses(request.resource, alias=target.alias)
    if clauses:
        condition_sql = " AND ".join(f"({clause})" for clause in clauses)
        try:
            insertion_index = where_parameter_insertion_index(target.select)
            target.select.where(condition_sql, append=True, copy=False, dialect=sqlglot_dialect(request.dialect))
        except Exception as exc:
            raise SQLDataAccessInjectionError(f"SQL 数据权限条件注入失败: {exc}") from exc
        params = insert_params(request.params, insertion_index, scope_params)
    else:
        params = tuple(request.params)
    return expression.sql(dialect=sqlglot_dialect(request.dialect)), params


def sqlglot_dialect(value: str | None) -> str:
    dialect = str(value or "sqlite").strip().lower()
    aliases = {
        "postgresql": "postgres",
        "psycopg": "postgres",
        "mysql+pymysql": "mysql",
        "sqlite3": "sqlite",
    }
    return aliases.get(dialect, dialect or "sqlite")


@dataclass(frozen=True)
class TargetTable:
    table: exp.Table
    select: exp.Select
    alias: str


def ensure_supported_select(expression: exp.Expression) -> None:
    if not isinstance(expression, exp.Select):
        raise SQLDataAccessInjectionError("仅支持单条 SELECT 查询")
    if expression.find(exp.Union) or expression.find(exp.Except) or expression.find(exp.Intersect):
        raise SQLDataAccessInjectionError("暂不支持 UNION/EXCEPT/INTERSECT 查询的数据权限注入")
    if expression.args.get("with"):
        raise SQLDataAccessInjectionError("暂不支持 WITH/CTE 查询的数据权限注入")
    if expression.find(exp.Insert) or expression.find(exp.Update) or expression.find(exp.Delete):
        raise SQLDataAccessInjectionError("仅支持只读 SELECT 查询")


def resolve_target_table(expression: exp.Expression, *, source_table: str = "", source_alias: str = "") -> TargetTable:
    normalized_source_table = optional_identifier(source_table, "source_table")
    normalized_source_alias = optional_identifier(source_alias, "source_alias")
    tables = [table for table in expression.find_all(exp.Table)]
    if not tables:
        raise SQLDataAccessInjectionError("SQL 查询缺少可注入的数据表")
    if normalized_source_alias:
        matches = [table for table in tables if table_alias(table) == normalized_source_alias]
        if len(matches) != 1:
            raise SQLDataAccessInjectionError("data_access.source_alias 未匹配到唯一数据表")
        table = matches[0]
    elif normalized_source_table:
        matches = [table for table in tables if table_name(table) == normalized_source_table]
        if len(matches) != 1:
            raise SQLDataAccessInjectionError("data_access.source_table 未匹配到唯一数据表")
        table = matches[0]
    else:
        table = default_target_table(expression)
        if table is None:
            raise SQLDataAccessInjectionError("多表 SQL 无法唯一识别主表")
    select = ancestor_select(table)
    if select is None:
        raise SQLDataAccessInjectionError("无法定位数据表所属 SELECT")
    alias = table_alias(table)
    if not alias:
        alias = table_name(table)
    if not normalized_identifier(alias):
        raise SQLDataAccessInjectionError("数据表别名不是合法 SQL 标识符")
    return TargetTable(table=table, select=select, alias=alias)


def default_target_table(expression: exp.Expression) -> exp.Table | None:
    from_clause = expression.args.get("from_")
    if isinstance(from_clause, exp.From):
        if isinstance(from_clause.this, exp.Table):
            return from_clause.this
    return None


def optional_identifier(value: str, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = normalized_identifier(text)
    if not normalized:
        raise SQLDataAccessInjectionError(f"data_access.{label} 不是合法 SQL 标识符")
    return normalized


def table_alias(table: exp.Table) -> str:
    alias = table.alias
    if alias:
        return str(alias)
    return ""


def table_name(table: exp.Table) -> str:
    return str(table.name or "").strip()


def ancestor_select(expression: exp.Expression) -> exp.Select | None:
    current = expression.parent
    while current is not None:
        if isinstance(current, exp.Select):
            return current
        current = current.parent
    return None


def where_parameter_insertion_index(select: exp.Select) -> int:
    count = 0
    for key in ("kind", "hint", "distinct", "expressions", "from_", "joins", "where"):
        count += placeholder_count(select.args.get(key))
    return count


def placeholder_count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, list):
        return sum(placeholder_count(item) for item in value)
    if isinstance(value, exp.Expression):
        return sum(1 for _ in value.find_all(exp.Placeholder))
    return 0


def insert_params(params: tuple[Any, ...], insertion_index: int, inserted: tuple[Any, ...]) -> tuple[Any, ...]:
    if not inserted:
        return tuple(params)
    safe_index = max(0, min(insertion_index, len(params)))
    return (*params[:safe_index], *inserted, *params[safe_index:])
