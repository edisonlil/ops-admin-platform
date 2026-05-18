from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_IMPORT_PATHS = (
    ROOT,
    ROOT / "packages" / "python" / "ops-admin-system" / "src",
    ROOT / "packages" / "python" / "ops-admin-cron" / "src",
    ROOT / "packages" / "python" / "ops-admin-identity-access" / "src",
    ROOT / "packages" / "python" / "ops-admin-basic-data" / "src",
    ROOT / "packages" / "python" / "ops-admin-organization" / "src",
    ROOT / "packages" / "python" / "ops-admin-authorization" / "src",
    ROOT / "packages" / "python" / "ops-admin-file-management" / "src",
    ROOT / "packages" / "python" / "ops-admin-audit-logging" / "src",
    ROOT / "packages" / "python" / "ops-admin-messaging" / "src",
    ROOT / "packages" / "python" / "ops-admin-ai-assets" / "src",
    ROOT / "packages" / "python" / "framework" / "ops-admin-ai-service-api" / "src",
    ROOT / "packages" / "python" / "framework" / "ops-admin-ai-runtime-core" / "src",
    ROOT / "packages" / "python" / "ops-admin-ai-applications" / "src",
    ROOT / "packages" / "python" / "ops-admin-ai-capabilities" / "src",
    ROOT / "packages" / "python" / "ops-admin-appearance" / "src",
    ROOT / "packages" / "python" / "ops-admin-llm-runtime" / "src",
)

for path in reversed(TEST_IMPORT_PATHS):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)
