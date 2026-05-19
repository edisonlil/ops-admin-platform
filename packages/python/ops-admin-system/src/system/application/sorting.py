from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class SortSpec:
    sort_by: str = ""
    sort_dir: str = ""

    @property
    def is_active(self) -> bool:
        return bool(self.sort_by and self.sort_dir)


class InvalidSortError(ValueError):
    pass


def parse_sort_params(sort_by: str | None = None, sort_dir: str | None = None) -> SortSpec:
    field = str(sort_by or "").strip()
    direction = str(sort_dir or "").strip().lower()
    if not field and not direction:
        return SortSpec()
    if direction not in {"asc", "desc"}:
        raise InvalidSortError("invalid sort direction")
    if not field:
        raise InvalidSortError("sort field is required")
    return SortSpec(sort_by=field, sort_dir=direction)


def build_order_by(
    sort: SortSpec | None,
    *,
    allowed: Mapping[str, str],
    default: str,
    tie_breaker: str = "id ASC",
) -> str:
    if not sort or not sort.is_active:
        return default
    column = allowed.get(sort.sort_by)
    if not column:
        raise InvalidSortError(f"unsupported sort field: {sort.sort_by}")
    direction = "ASC" if sort.sort_dir == "asc" else "DESC"
    order_by = f"{column} {direction}"
    return f"{order_by}, {tie_breaker}" if tie_breaker else order_by


def sort_dict_items(
    items: Sequence[Mapping[str, Any]],
    sort_by: str | None = None,
    sort_dir: str | None = None,
    *,
    allowed: Mapping[str, str],
) -> list[dict[str, Any]]:
    sort = parse_sort_params(sort_by, sort_dir)
    normalized_items = [dict(item) for item in items]
    if not sort.is_active:
        return normalized_items
    key = allowed.get(sort.sort_by)
    if not key:
        raise InvalidSortError(f"unsupported sort field: {sort.sort_by}")
    direction = -1 if sort.sort_dir == "desc" else 1
    return sorted(normalized_items, key=lambda item: sortable_value(item.get(key)), reverse=direction < 0)


def sortable_value(value: Any) -> tuple[int, Any]:
    if value is None:
        return (0, "")
    if isinstance(value, bool):
        return (1, int(value))
    if isinstance(value, (int, float)):
        return (1, value)
    return (1, str(value).lower())
