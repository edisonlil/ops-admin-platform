from __future__ import annotations

from system.infrastructure.config import (
    database_backend,
    default_use_keywords_recall,
    resolve_database_url,
    resolve_db_path,
)
from system.infrastructure.persistence.connection import connect, is_database_url
from system.infrastructure.persistence.connection import configure_sql_observer
from system.infrastructure.persistence.dialect import table_exists
