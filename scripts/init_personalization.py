from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.module_registry import module_init_tasks
from system.application.database import connect, resolve_database_url, resolve_db_path


def main() -> None:
    target = resolve_database_url() or resolve_db_path()
    with connect(target, readonly=False) as conn:
        module_init_tasks()["personalization"](conn)
    print(f"personalization storage initialized: {target}")


if __name__ == "__main__":
    main()
