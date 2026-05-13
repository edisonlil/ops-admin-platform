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
            FakeEntryPoint("file_management", "file_management.entrypoints:router", fake_router("file_management")),
            FakeEntryPoint("system", "system.entrypoints:router", fake_router("system")),
            FakeEntryPoint("llm_runtime", "llm_runtime.entrypoints:router", fake_router("llm_runtime")),
            FakeEntryPoint("ai_assets", "ai_assets.entrypoints:router", fake_router("ai_assets")),
            FakeEntryPoint("messaging", "messaging.entrypoints:router", fake_router("messaging")),
            FakeEntryPoint("identity_access", "identity_access.entrypoints:router", fake_router("identity_access")),
        ]

        with mock.patch("api.module_registry.entry_points", return_value=entrypoints):
            routers = module_registry.module_routers()

        self.assertEqual(len(routers), 9)
        self.assertEqual(
            loaded,
            [
                "system",
                "cron",
                "identity_access",
                "basic_data",
                "file_management",
                "messaging",
                "llm_runtime",
                "ai_assets",
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
                "basic_data",
                "basic_data.entrypoints:init_tasks",
                lambda: (lambda: {"basic_data": lambda conn: None}),
            ),
            FakeEntryPoint(
                "file_management",
                "file_management.entrypoints:init_tasks",
                lambda: (lambda: {"file_management": lambda conn: None}),
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
        ]

        with mock.patch("api.module_registry.entry_points", return_value=entrypoints):
            tasks = module_registry.module_init_tasks()

        self.assertEqual(
            set(tasks),
            {"cron", "identity_access", "basic_data", "file_management", "appearance", "messaging", "llm_runtime", "ai_assets"},
        )


if __name__ == "__main__":
    unittest.main()
