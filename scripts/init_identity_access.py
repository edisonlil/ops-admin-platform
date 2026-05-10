from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.module_registry import module_init_tasks
from identity_access.infrastructure.persistence.common import auth_database_target, connect


def main() -> None:
    target = auth_database_target()
    with connect(target, readonly=False) as conn:
        module_init_tasks()["identity_access"](conn)
    print(f"identity_access storage initialized: {target}")


if __name__ == "__main__":
    main()
