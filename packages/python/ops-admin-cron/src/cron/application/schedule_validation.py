from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from cron.domain.exceptions import CronDomainError
from cron.domain.models import TRIGGER_TYPE_CRON, TRIGGER_TYPE_DATE, TRIGGER_TYPE_INTERVAL, CronSchedule


def validate_schedule_details(schedule: CronSchedule) -> None:
    try:
        ZoneInfo(schedule.timezone)
    except ZoneInfoNotFoundError as exc:
        raise CronDomainError(f"invalid timezone: {schedule.timezone}") from exc

    if schedule.trigger_type == TRIGGER_TYPE_INTERVAL:
        validate_interval_expression(schedule.trigger_expression)
        return
    if schedule.trigger_type == TRIGGER_TYPE_DATE:
        validate_date_expression(schedule.trigger_expression)
        return
    if schedule.trigger_type == TRIGGER_TYPE_CRON:
        validate_cron_expression(schedule.trigger_expression)


def validate_interval_expression(expression: str) -> None:
    try:
        seconds = int(expression)
    except ValueError as exc:
        raise CronDomainError("interval trigger expression must be positive seconds") from exc
    if seconds <= 0:
        raise CronDomainError("interval trigger expression must be positive seconds")


def validate_date_expression(expression: str) -> None:
    normalized = expression.strip().replace("Z", "+00:00")
    if not normalized:
        raise CronDomainError("date trigger expression is required")
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise CronDomainError("date trigger expression must be an ISO datetime") from exc


def validate_cron_expression(expression: str) -> None:
    fields = expression.split()
    if len(fields) not in {5, 6}:
        raise CronDomainError("cron expression must have 5 fields or 6 fields with seconds")
    if any(not field.strip() for field in fields):
        raise CronDomainError("cron expression fields cannot be empty")
