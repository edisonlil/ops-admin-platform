from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cron.domain.models import (
    CronAttempt,
    CronRun,
    CronSchedule,
    CronTask,
    CronTaskDetail,
    ExternalScheduleBinding,
    ATTEMPT_STATUS_RUNNING,
    RUN_STATUS_FAILED,
    RUN_STATUS_PENDING,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCEEDED,
    TASK_STATUS_DISABLED,
    TASK_STATUS_ENABLED,
)
from cron.infrastructure.persistence.bootstrap import require_cron_schema
from system.application.database import connect, resolve_database_url, resolve_db_path


def database_target() -> str | Path:
    return resolve_database_url() or resolve_db_path()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def save_task(
    *,
    tenant_id: int,
    payload: dict[str, Any],
    actor: str,
    actor_id: int | None,
) -> CronTaskDetail:
    timestamp = now_iso()
    task_id = int(payload.get("id") or 0)
    task_values = (
        str(payload.get("task_key") or "").strip(),
        str(payload.get("name") or "").strip(),
        str(payload.get("description") or "").strip(),
        str(payload.get("status") or "draft").strip() or "draft",
        str(payload.get("execution_target") or "").strip(),
        int(payload.get("payload_schema_version") or 1),
        encode_json(payload.get("default_payload") if isinstance(payload.get("default_payload"), dict) else {}),
        str(payload.get("concurrency_policy") or "forbid").strip() or "forbid",
        int(payload.get("timeout_seconds") or 300),
        int(payload.get("max_attempts") or 1),
        int(payload.get("retry_delay_seconds") or 0),
        float(payload.get("retry_backoff_multiplier") or 1),
        str(payload.get("misfire_policy") or "skip").strip() or "skip",
        actor,
        actor_id,
        timestamp,
    )
    schedule_payload = payload.get("schedule") if isinstance(payload.get("schedule"), dict) else None
    with connect(database_target(), readonly=False) as conn:
        require_cron_schema(conn)
        if task_id:
            conn.execute(
                """
                UPDATE cron_tasks
                SET task_key = ?, name = ?, description = ?, status = ?,
                    execution_target = ?, payload_schema_version = ?, default_payload_json = ?,
                    concurrency_policy = ?, timeout_seconds = ?, max_attempts = ?,
                    retry_delay_seconds = ?, retry_backoff_multiplier = ?, misfire_policy = ?,
                    editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
                WHERE id = ? AND tenant_id = ? AND deleted = 0
                """,
                (*task_values, task_id, tenant_id),
            )
            saved_id = task_id
        else:
            cursor = conn.execute(
                """
                INSERT INTO cron_tasks (
                    tenant_id, task_key, name, description, status, execution_target,
                    payload_schema_version, default_payload_json, concurrency_policy,
                    timeout_seconds, max_attempts, retry_delay_seconds, retry_backoff_multiplier,
                    misfire_policy, creator, creator_id, editor, editor_id, create_time, update_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    *task_values[:13],
                    actor,
                    actor_id,
                    actor,
                    actor_id,
                    timestamp,
                    timestamp,
                ),
            )
            saved_id = inserted_id(conn, cursor, "cron_tasks", timestamp, actor)
        if schedule_payload:
            upsert_schedule_row(
                conn,
                tenant_id=tenant_id,
                task_id=saved_id,
                payload=schedule_payload,
                actor=actor,
                actor_id=actor_id,
                timestamp=timestamp,
            )
    detail = get_task_detail(tenant_id=tenant_id, task_id=saved_id)
    if detail is None:
        raise RuntimeError("cron task save failed")
    return detail


def upsert_schedule_row(
    conn: Any,
    *,
    tenant_id: int,
    task_id: int,
    payload: dict[str, Any],
    actor: str,
    actor_id: int | None,
    timestamp: str,
) -> None:
    existing = conn.execute(
        "SELECT id FROM cron_schedules WHERE tenant_id = ? AND task_id = ? AND deleted = 0",
        (tenant_id, task_id),
    ).fetchone()
    values = (
        str(payload.get("trigger_type") or "cron").strip() or "cron",
        str(payload.get("trigger_expression") or "").strip(),
        str(payload.get("timezone") or "UTC").strip() or "UTC",
        none_or_str(payload.get("start_time")),
        none_or_str(payload.get("end_time")),
        none_or_str(payload.get("next_fire_time")),
        actor,
        actor_id,
        timestamp,
    )
    if existing:
        conn.execute(
            """
            UPDATE cron_schedules
            SET trigger_type = ?, trigger_expression = ?, timezone = ?, start_time = ?,
                end_time = ?, next_fire_time = ?, editor = ?, editor_id = ?,
                update_time = ?, lock_version = lock_version + 1
            WHERE id = ?
            """,
            (*values, int(existing["id"])),
        )
        return
    conn.execute(
        """
        INSERT INTO cron_schedules (
            tenant_id, task_id, trigger_type, trigger_expression, timezone,
            start_time, end_time, next_fire_time, creator, creator_id, editor,
            editor_id, create_time, update_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id,
            task_id,
            *values[:6],
            actor,
            actor_id,
            actor,
            actor_id,
            timestamp,
            timestamp,
        ),
    )


def list_tasks(*, tenant_id: int, page: int, page_size: int, status: str | None = None) -> tuple[list[CronTaskDetail], int]:
    offset = (page - 1) * page_size
    params: list[Any] = [tenant_id]
    status_filter = ""
    if status:
        status_filter = " AND status = ?"
        params.append(status)
    with connect(database_target(), readonly=True) as conn:
        require_cron_schema(conn)
        total_row = conn.execute(
            f"SELECT COUNT(*) AS total FROM cron_tasks WHERE tenant_id = ? AND deleted = 0{status_filter}",
            tuple(params),
        ).fetchone()
        rows = conn.execute(
            f"""
            SELECT *
            FROM cron_tasks
            WHERE tenant_id = ? AND deleted = 0{status_filter}
            ORDER BY update_time DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            tuple([*params, page_size, offset]),
        ).fetchall()
        details = [row_to_task_detail(conn, dict(row)) for row in rows]
    return details, int(total_row["total"] if total_row else 0)


def list_enabled_task_details() -> list[CronTaskDetail]:
    with connect(database_target(), readonly=True) as conn:
        require_cron_schema(conn)
        rows = conn.execute(
            """
            SELECT *
            FROM cron_tasks
            WHERE status = ? AND deleted = 0
            ORDER BY tenant_id ASC, id ASC
            """,
            (TASK_STATUS_ENABLED,),
        ).fetchall()
        return [row_to_task_detail(conn, dict(row)) for row in rows]


def get_task_detail(*, tenant_id: int, task_id: int) -> CronTaskDetail | None:
    with connect(database_target(), readonly=True) as conn:
        require_cron_schema(conn)
        row = conn.execute(
            "SELECT * FROM cron_tasks WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (task_id, tenant_id),
        ).fetchone()
        if not row:
            return None
        return row_to_task_detail(conn, dict(row))


def get_task_by_key(*, tenant_id: int, task_key: str) -> CronTaskDetail | None:
    with connect(database_target(), readonly=True) as conn:
        require_cron_schema(conn)
        row = conn.execute(
            "SELECT * FROM cron_tasks WHERE task_key = ? AND tenant_id = ? AND deleted = 0",
            (task_key, tenant_id),
        ).fetchone()
        if not row:
            return None
        return row_to_task_detail(conn, dict(row))


def set_task_status(*, tenant_id: int, task_id: int, status: str, actor: str, actor_id: int | None) -> CronTaskDetail | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_cron_schema(conn)
        conn.execute(
            """
            UPDATE cron_tasks
            SET status = ?, editor = ?, editor_id = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (status, actor, actor_id, timestamp, task_id, tenant_id),
        )
    return get_task_detail(tenant_id=tenant_id, task_id=task_id)


def delete_task(*, tenant_id: int, task_id: int, actor: str, actor_id: int | None) -> CronTaskDetail | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_cron_schema(conn)
        existing = conn.execute(
            "SELECT * FROM cron_tasks WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (task_id, tenant_id),
        ).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE cron_tasks
            SET deleted = 1, status = ?, editor = ?, editor_id = ?,
                update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ?
            """,
            (TASK_STATUS_DISABLED, actor, actor_id, timestamp, task_id, tenant_id),
        )
    return CronTaskDetail(row_to_task(dict(existing)), None)


def create_manual_run(
    *,
    tenant_id: int,
    task_id: int,
    payload: dict[str, Any],
    idempotency_key: str,
    actor: str,
    actor_id: int | None,
) -> CronRun:
    timestamp = now_iso()
    fire_time = timestamp
    with connect(database_target(), readonly=False) as conn:
        require_cron_schema(conn)
        task_row = conn.execute(
            "SELECT * FROM cron_tasks WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (task_id, tenant_id),
        ).fetchone()
        if not task_row:
            raise LookupError("cron task not found")
        existing = conn.execute(
            """
            SELECT *
            FROM cron_runs
            WHERE tenant_id = ? AND task_id = ? AND idempotency_key = ? AND deleted = 0
            """,
            (tenant_id, task_id, idempotency_key),
        ).fetchone()
        if existing:
            return row_to_run(dict(existing))
        schedule_row = conn.execute(
            "SELECT id FROM cron_schedules WHERE tenant_id = ? AND task_id = ? AND deleted = 0",
            (tenant_id, task_id),
        ).fetchone()
        cursor = conn.execute(
            """
            INSERT INTO cron_runs (
                tenant_id, task_id, schedule_id, fire_time, status, trigger_source,
                idempotency_key, payload_json, creator, creator_id, editor, editor_id,
                create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                task_id,
                int(schedule_row["id"]) if schedule_row else None,
                fire_time,
                RUN_STATUS_PENDING,
                "manual",
                idempotency_key,
                encode_json(payload),
                actor,
                actor_id,
                actor,
                actor_id,
                timestamp,
                timestamp,
            ),
        )
        run_id = inserted_id(conn, cursor, "cron_runs", timestamp, actor)
        row = conn.execute("SELECT * FROM cron_runs WHERE id = ?", (run_id,)).fetchone()
    return row_to_run(dict(row))


def create_scheduled_run(
    *,
    tenant_id: int,
    task_id: int,
    schedule_id: int,
    fire_time: str,
    payload: dict[str, Any],
    idempotency_key: str,
    actor: str,
) -> CronRun:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_cron_schema(conn)
        existing = conn.execute(
            """
            SELECT *
            FROM cron_runs
            WHERE tenant_id = ? AND task_id = ? AND idempotency_key = ? AND deleted = 0
            """,
            (tenant_id, task_id, idempotency_key),
        ).fetchone()
        if existing:
            return row_to_run(dict(existing))
        cursor = conn.execute(
            """
            INSERT INTO cron_runs (
                tenant_id, task_id, schedule_id, fire_time, status, trigger_source,
                idempotency_key, payload_json, creator, editor, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                task_id,
                schedule_id,
                fire_time,
                RUN_STATUS_PENDING,
                "schedule",
                idempotency_key,
                encode_json(payload),
                actor,
                actor,
                timestamp,
                timestamp,
            ),
        )
        run_id = inserted_id(conn, cursor, "cron_runs", timestamp, actor)
        row = conn.execute("SELECT * FROM cron_runs WHERE id = ?", (run_id,)).fetchone()
    return row_to_run(dict(row))


def mark_run_running(*, tenant_id: int, run_id: int, actor: str) -> CronRun | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_cron_schema(conn)
        conn.execute(
            """
            UPDATE cron_runs
            SET status = ?, started_time = COALESCE(started_time, ?),
                editor = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (RUN_STATUS_RUNNING, timestamp, actor, timestamp, run_id, tenant_id),
        )
        row = conn.execute(
            "SELECT * FROM cron_runs WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (run_id, tenant_id),
        ).fetchone()
    return row_to_run(dict(row)) if row else None


def start_attempt(*, tenant_id: int, run_id: int, worker_id: str, actor: str) -> CronAttempt:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_cron_schema(conn)
        row = conn.execute(
            """
            SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt
            FROM cron_attempts
            WHERE tenant_id = ? AND run_id = ? AND deleted = 0
            """,
            (tenant_id, run_id),
        ).fetchone()
        attempt_number = int(row["next_attempt"] if row else 1)
        cursor = conn.execute(
            """
            INSERT INTO cron_attempts (
                tenant_id, run_id, attempt_number, status, worker_id, started_time,
                creator, editor, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                run_id,
                attempt_number,
                ATTEMPT_STATUS_RUNNING,
                worker_id,
                timestamp,
                actor,
                actor,
                timestamp,
                timestamp,
            ),
        )
        attempt_id = inserted_id(conn, cursor, "cron_attempts", timestamp, actor)
        attempt = conn.execute("SELECT * FROM cron_attempts WHERE id = ?", (attempt_id,)).fetchone()
    return row_to_attempt(dict(attempt))


def complete_attempt(
    *,
    tenant_id: int,
    attempt_id: int,
    status: str,
    error_code: str,
    error_message: str,
    actor: str,
) -> CronAttempt | None:
    timestamp = now_iso()
    with connect(database_target(), readonly=False) as conn:
        require_cron_schema(conn)
        conn.execute(
            """
            UPDATE cron_attempts
            SET status = ?, finished_time = ?, error_code = ?, error_message = ?,
                editor = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (status, timestamp, error_code, error_message, actor, timestamp, attempt_id, tenant_id),
        )
        row = conn.execute(
            "SELECT * FROM cron_attempts WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (attempt_id, tenant_id),
        ).fetchone()
    return row_to_attempt(dict(row)) if row else None


def complete_run(
    *,
    tenant_id: int,
    run_id: int,
    status: str,
    result: dict[str, Any] | None = None,
    failure_code: str,
    failure_message: str,
    actor: str,
) -> CronRun | None:
    timestamp = now_iso()
    normalized_status = status if status in {RUN_STATUS_SUCCEEDED, RUN_STATUS_FAILED} else RUN_STATUS_FAILED
    with connect(database_target(), readonly=False) as conn:
        require_cron_schema(conn)
        conn.execute(
            """
            UPDATE cron_runs
            SET status = ?, finished_time = ?, result_json = ?, failure_code = ?, failure_message = ?,
                editor = ?, update_time = ?, lock_version = lock_version + 1
            WHERE id = ? AND tenant_id = ? AND deleted = 0
            """,
            (
                normalized_status,
                timestamp,
                encode_json(result if isinstance(result, dict) else {}),
                failure_code,
                failure_message,
                actor,
                timestamp,
                run_id,
                tenant_id,
            ),
        )
        row = conn.execute(
            "SELECT * FROM cron_runs WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (run_id, tenant_id),
        ).fetchone()
    return row_to_run(dict(row)) if row else None


def list_runs(*, tenant_id: int, task_id: int | None, page: int, page_size: int) -> tuple[list[CronRun], int]:
    offset = (page - 1) * page_size
    params: list[Any] = [tenant_id]
    task_filter = ""
    if task_id is not None:
        task_filter = " AND task_id = ?"
        params.append(task_id)
    with connect(database_target(), readonly=True) as conn:
        require_cron_schema(conn)
        total_row = conn.execute(
            f"SELECT COUNT(*) AS total FROM cron_runs WHERE tenant_id = ? AND deleted = 0{task_filter}",
            tuple(params),
        ).fetchone()
        rows = conn.execute(
            f"""
            SELECT *
            FROM cron_runs
            WHERE tenant_id = ? AND deleted = 0{task_filter}
            ORDER BY fire_time DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            tuple([*params, page_size, offset]),
        ).fetchall()
    return [row_to_run(dict(row)) for row in rows], int(total_row["total"] if total_row else 0)


def get_run(*, tenant_id: int, run_id: int) -> CronRun | None:
    with connect(database_target(), readonly=True) as conn:
        require_cron_schema(conn)
        row = conn.execute(
            "SELECT * FROM cron_runs WHERE id = ? AND tenant_id = ? AND deleted = 0",
            (run_id, tenant_id),
        ).fetchone()
    return row_to_run(dict(row)) if row else None


def list_attempts(*, tenant_id: int, run_id: int) -> list[CronAttempt]:
    with connect(database_target(), readonly=True) as conn:
        require_cron_schema(conn)
        rows = conn.execute(
            """
            SELECT *
            FROM cron_attempts
            WHERE tenant_id = ? AND run_id = ? AND deleted = 0
            ORDER BY attempt_number ASC
            """,
            (tenant_id, run_id),
        ).fetchall()
    return [row_to_attempt(dict(row)) for row in rows]


def row_to_task_detail(conn: Any, task_row: dict[str, Any]) -> CronTaskDetail:
    schedule_row = conn.execute(
        "SELECT * FROM cron_schedules WHERE tenant_id = ? AND task_id = ? AND deleted = 0",
        (int(task_row["tenant_id"]), int(task_row["id"])),
    ).fetchone()
    return CronTaskDetail(
        task=row_to_task(task_row),
        schedule=row_to_schedule(dict(schedule_row)) if schedule_row else None,
    )


def row_to_task(row: dict[str, Any]) -> CronTask:
    return CronTask(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        task_key=str(row.get("task_key") or ""),
        name=str(row.get("name") or ""),
        description=str(row.get("description") or ""),
        status=str(row.get("status") or "draft"),
        execution_target=str(row.get("execution_target") or ""),
        payload_schema_version=int(row.get("payload_schema_version") or 1),
        default_payload=decode_json(row.get("default_payload_json")),
        concurrency_policy=str(row.get("concurrency_policy") or "forbid"),
        timeout_seconds=int(row.get("timeout_seconds") or 300),
        max_attempts=int(row.get("max_attempts") or 1),
        retry_delay_seconds=int(row.get("retry_delay_seconds") or 0),
        retry_backoff_multiplier=float(row.get("retry_backoff_multiplier") or 1),
        misfire_policy=str(row.get("misfire_policy") or "skip"),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_schedule(row: dict[str, Any]) -> CronSchedule:
    return CronSchedule(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        task_id=int(row["task_id"]),
        trigger_type=str(row.get("trigger_type") or "cron"),
        trigger_expression=str(row.get("trigger_expression") or ""),
        timezone=str(row.get("timezone") or "UTC"),
        start_time=none_or_str(row.get("start_time")),
        end_time=none_or_str(row.get("end_time")),
        next_fire_time=none_or_str(row.get("next_fire_time")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_run(row: dict[str, Any]) -> CronRun:
    return CronRun(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        task_id=int(row["task_id"]),
        schedule_id=int(row["schedule_id"]) if row.get("schedule_id") is not None else None,
        fire_time=str(row.get("fire_time") or ""),
        status=str(row.get("status") or RUN_STATUS_PENDING),
        trigger_source=str(row.get("trigger_source") or "manual"),
        idempotency_key=str(row.get("idempotency_key") or ""),
        payload=decode_json(row.get("payload_json")),
        result=decode_json(row.get("result_json")),
        started_time=none_or_str(row.get("started_time")),
        finished_time=none_or_str(row.get("finished_time")),
        failure_code=str(row.get("failure_code") or ""),
        failure_message=str(row.get("failure_message") or ""),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_attempt(row: dict[str, Any]) -> CronAttempt:
    return CronAttempt(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        run_id=int(row["run_id"]),
        attempt_number=int(row["attempt_number"]),
        status=str(row.get("status") or "running"),
        worker_id=str(row.get("worker_id") or ""),
        started_time=str(row.get("started_time") or ""),
        finished_time=none_or_str(row.get("finished_time")),
        error_code=str(row.get("error_code") or ""),
        error_message=str(row.get("error_message") or ""),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
    )


def row_to_binding(row: dict[str, Any]) -> ExternalScheduleBinding:
    return ExternalScheduleBinding(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        task_id=int(row["task_id"]),
        scheduler_type=str(row.get("scheduler_type") or ""),
        external_id=str(row.get("external_id") or ""),
        status=str(row.get("status") or "active"),
        metadata=decode_json(row.get("metadata_json")),
        create_time=str(row.get("create_time") or ""),
        update_time=str(row.get("update_time") or ""),
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


def none_or_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
