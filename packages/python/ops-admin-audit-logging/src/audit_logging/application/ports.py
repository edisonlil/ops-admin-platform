from __future__ import annotations

from typing import Any, Protocol

from audit_logging.domain.models import AuditLoggingSettings
from system.application.data_access import DataAccessPredicate


class AuditLogRepository(Protocol):
    def insert_many(self, records: list[dict[str, Any]]) -> None:
        ...

    def list_logs(
        self,
        *,
        category: str,
        tenant_id: int | None,
        page: int,
        page_size: int,
        keyword: str,
        outcome: str,
        severity: str,
        data_scope: DataAccessPredicate | None,
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        ...

    def list_settings(self) -> list[AuditLoggingSettings]:
        ...

    def get_effective_settings(self, tenant_id: int) -> AuditLoggingSettings:
        ...

    def save_settings(self, tenant_id: int, payload: dict[str, Any], *, actor: str, actor_id: int | None) -> AuditLoggingSettings:
        ...
