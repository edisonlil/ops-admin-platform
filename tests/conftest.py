from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SRC_PATHS = (
    ROOT / "packages" / "python" / "ops-admin-system" / "src",
    ROOT / "packages" / "python" / "ops-admin-identity-access" / "src",
    ROOT / "packages" / "python" / "ops-admin-appearance" / "src",
    ROOT / "packages" / "python" / "ops-admin-llm-runtime" / "src",
)

for path in reversed(PACKAGE_SRC_PATHS):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)
