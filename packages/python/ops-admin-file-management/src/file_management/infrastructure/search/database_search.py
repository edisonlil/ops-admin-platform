from __future__ import annotations

from file_management.domain.models import ManagedFile
from file_management.infrastructure.persistence import repositories


class DatabaseFileSearch:
    def search(self, *, tenant_id: int, keyword: str, page: int, page_size: int, file_ids: list[int] | None = None) -> tuple[list[ManagedFile], int]:
        return repositories.list_files(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            file_ids=file_ids,
        )
