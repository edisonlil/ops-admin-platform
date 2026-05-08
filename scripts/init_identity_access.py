from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from identity_access.infrastructure.persistence.common import (  # noqa: E402
    auth_database_target,
    connect,
    initialize_auth_storage,
)


def main() -> None:
    target = auth_database_target()
    with connect(target, readonly=False) as conn:
        initialize_auth_storage(conn)
    print(f"identity_access storage initialized: {target}")


if __name__ == "__main__":
    main()
