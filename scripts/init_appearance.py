from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from appearance.infrastructure.persistence.bootstrap import ensure_appearance_schema  # noqa: E402
from system.application.database import connect, resolve_database_url, resolve_db_path  # noqa: E402


def main() -> None:
    target = resolve_database_url() or resolve_db_path()
    with connect(target, readonly=False) as conn:
        ensure_appearance_schema(conn)
    print(f"appearance storage initialized: {target}")


if __name__ == "__main__":
    main()
