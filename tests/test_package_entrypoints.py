from __future__ import annotations

import unittest
from unittest import mock

from fastapi import APIRouter


class FakeEntryPoint:
    def __init__(self, name: str, value: str, loader: object) -> None:
        self.name = name
        self.value = value
        self.loader = loader

    def load(self) -> object:
        if callable(self.loader):
            return self.loader()
        return self.loader


class PackageEntrypointTests(unittest.TestCase):
    def test_module_registry_composes_routers_in_starter_order(self) -> None:
        from api import module_registry

        loaded: list[str] = []

        def fake_router(name: str) -> object:
            def load_router() -> APIRouter:
                loaded.append(name)
                return APIRouter()

            return load_router

        entrypoints = [
            FakeEntryPoint("appearance", "appearance.entrypoints:router", fake_router("appearance")),
            FakeEntryPoint("cron", "cron.entrypoints:router", fake_router("cron")),
            FakeEntryPoint("basic_data", "basic_data.entrypoints:router", fake_router("basic_data")),
            FakeEntryPoint("metadata_support", "metadata_support.entrypoints:router", fake_router("metadata_support")),
            FakeEntryPoint("personalization", "personalization.entrypoints:router", fake_router("personalization")),
            FakeEntryPoint("page_designer", "page_designer.entrypoints:router", fake_router("page_designer")),
            FakeEntryPoint("file_management", "file_management.entrypoints:router", fake_router("file_management")),
            FakeEntryPoint("datasets", "datasets.entrypoints:router", fake_router("datasets")),
            FakeEntryPoint("audit_logging", "audit_logging.entrypoints:router", fake_router("audit_logging")),
            FakeEntryPoint("system", "system.entrypoints:router", fake_router("system")),
            FakeEntryPoint("llm_runtime", "llm_runtime.entrypoints:router", fake_router("llm_runtime")),
            FakeEntryPoint("ai_assets", "ai_assets.entrypoints:router", fake_router("ai_assets")),
            FakeEntryPoint("ai_applications", "ai_applications.entrypoints:router", fake_router("ai_applications")),
            FakeEntryPoint("ai_capabilities", "ai_capabilities.entrypoints:router", fake_router("ai_capabilities")),
            FakeEntryPoint("messaging", "messaging.entrypoints:router", fake_router("messaging")),
            FakeEntryPoint("identity_access", "identity_access.entrypoints:router", fake_router("identity_access")),
            FakeEntryPoint("organization", "organization.entrypoints:router", fake_router("organization")),
            FakeEntryPoint("authorization", "authorization.entrypoints:router", fake_router("authorization")),
        ]

        with mock.patch("api.module_registry.entry_points", return_value=entrypoints):
            routers = module_registry.module_routers()

        self.assertEqual(len(routers), 18)
        self.assertEqual(
            loaded,
            [
                "system",
                "cron",
                "identity_access",
                "organization",
                "authorization",
                "basic_data",
                "metadata_support",
                "personalization",
                "page_designer",
                "file_management",
                "datasets",
                "audit_logging",
                "messaging",
                "llm_runtime",
                "ai_assets",
                "ai_applications",
                "ai_capabilities",
                "appearance",
            ],
        )

    def test_module_registry_composes_init_tasks(self) -> None:
        from api import module_registry

        entrypoints = [
            FakeEntryPoint(
                "cron",
                "cron.entrypoints:init_tasks",
                lambda: (lambda: {"cron": lambda conn: None}),
            ),
            FakeEntryPoint(
                "identity_access",
                "identity_access.entrypoints:init_tasks",
                lambda: (lambda: {"identity_access": lambda conn: None}),
            ),
            FakeEntryPoint(
                "organization",
                "organization.entrypoints:init_tasks",
                lambda: (lambda: {"organization": lambda conn: None}),
            ),
            FakeEntryPoint(
                "authorization",
                "authorization.entrypoints:init_tasks",
                lambda: (lambda: {"authorization": lambda conn: None}),
            ),
            FakeEntryPoint(
                "basic_data",
                "basic_data.entrypoints:init_tasks",
                lambda: (lambda: {"basic_data": lambda conn: None}),
            ),
            FakeEntryPoint(
                "metadata_support",
                "metadata_support.entrypoints:init_tasks",
                lambda: (lambda: {"metadata_support": lambda conn: None}),
            ),
            FakeEntryPoint(
                "personalization",
                "personalization.entrypoints:init_tasks",
                lambda: (lambda: {"personalization": lambda conn: None}),
            ),
            FakeEntryPoint(
                "page_designer",
                "page_designer.entrypoints:init_tasks",
                lambda: (lambda: {"page_designer": lambda conn: None}),
            ),
            FakeEntryPoint(
                "file_management",
                "file_management.entrypoints:init_tasks",
                lambda: (lambda: {"file_management": lambda conn: None}),
            ),
            FakeEntryPoint(
                "datasets",
                "datasets.entrypoints:init_tasks",
                lambda: (lambda: {"datasets": lambda conn: None}),
            ),
            FakeEntryPoint(
                "audit_logging",
                "audit_logging.entrypoints:init_tasks",
                lambda: (lambda: {"audit_logging": lambda conn: None}),
            ),
            FakeEntryPoint(
                "appearance",
                "appearance.entrypoints:init_tasks",
                lambda: (lambda: {"appearance": lambda conn: None}),
            ),
            FakeEntryPoint(
                "messaging",
                "messaging.entrypoints:init_tasks",
                lambda: (lambda: {"messaging": lambda conn: None}),
            ),
            FakeEntryPoint(
                "ai_assets",
                "ai_assets.entrypoints:init_tasks",
                lambda: (lambda: {"ai_assets": lambda conn: None}),
            ),
            FakeEntryPoint(
                "ai_applications",
                "ai_applications.entrypoints:init_tasks",
                lambda: (lambda: {"ai_applications": lambda conn: None}),
            ),
            FakeEntryPoint(
                "ai_capabilities",
                "ai_capabilities.entrypoints:init_tasks",
                lambda: (lambda: {"ai_capabilities": lambda conn: None}),
            ),
        ]

        with mock.patch("api.module_registry.entry_points", return_value=entrypoints):
            tasks = module_registry.module_init_tasks()

        self.assertEqual(
            set(tasks),
            {
                "cron",
                "identity_access",
                "organization",
                "authorization",
                "basic_data",
                "metadata_support",
                "personalization",
                "page_designer",
                "file_management",
                "datasets",
                "audit_logging",
                "appearance",
                "messaging",
                "llm_runtime",
                "ai_assets",
                "ai_applications",
                "ai_capabilities",
            },
        )


if __name__ == "__main__":
    unittest.main()
