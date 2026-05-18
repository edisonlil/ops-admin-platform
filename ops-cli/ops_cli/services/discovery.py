"""
Module discovery service - unified module discovery for ops-cli.

Discovers available modules from:
- scripts/init_*.py (init scripts)
- packages/python/ops-admin-*/src/<module_name>/ (package structure)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ModuleInfo:
    """Information about a discovered module."""
    name: str
    init_script: str | None = None  # e.g., "init_audit_logging.py"
    has_package: bool = False        # True if packages/python/ops-admin-<name>/src/<name>/ exists
    package_path: str | None = None  # Full path to the module's src directory

    @property
    def has_init_script(self) -> bool:
        return self.init_script is not None


@dataclass
class ModuleDiscoveryResult:
    """Result of module discovery."""
    modules: dict[str, ModuleInfo] = field(default_factory=dict)
    scaffold_root: Path | None = None

    def get_module_names(self) -> list[str]:
        """Get sorted list of all module names."""
        return sorted(self.modules.keys())

    def get_modules_with_init(self) -> dict[str, str]:
        """Get dict of module_name -> init_script_name for modules that have init scripts."""
        return {
            name: info.init_script
            for name, info in self.modules.items()
            if info.has_init_script
        }

    def get_all_pythonpath_parts(self) -> list[str]:
        """Get all PYTHONPATH parts for modules that have packages."""
        return [
            info.package_path
            for info in self.modules.values()
            if info.package_path
        ]


class ModuleDiscoveryService:
    """
    Unified module discovery service.

    Discovers modules from two sources:
    1. scripts/init_*.py - init scripts
    2. packages/python/ops-admin-*/src/<module_name>/ - package structure

    Usage:
        service = ModuleDiscoveryService(scaffold_root=Path("/path/to/scaffold"))
        result = service.discover()
        print(result.get_module_names())
        print(result.get_modules_with_init())
    """

    # Module display order (system modules first, then alphabetical)
    # Use underscores for multi-word module names
    _DISPLAY_PRIORITY = [
        "system",
        "identity_access",
        "organization",
        "authorization",
        "basic_data",
        "file_management",
        "messaging",
        "llm_runtime",
        "ai_assets",
        "ai_applications",
        "ai_capabilities",
        "appearance",
        "audit_logging",
        "cron",
    ]

    def __init__(self, scaffold_root: Path | None = None):
        """
        Initialize the discovery service.

        Args:
            scaffold_root: Root path of the scaffold. Defaults to the ops-cli package root
                          (when running from the scaffold repo itself).
        """
        if scaffold_root is None:
            # Default to the ops-cli package root (this repo)
            self.scaffold_root = Path(__file__).parent.parent.parent
        else:
            self.scaffold_root = scaffold_root

    def discover(self) -> ModuleDiscoveryResult:
        """
        Discover all available modules.

        Returns:
            ModuleDiscoveryResult containing all discovered modules.
        """
        result = ModuleDiscoveryResult(scaffold_root=self.scaffold_root)

        # Scan scripts/init_*.py
        self._discover_from_scripts(result)

        # Scan packages/python/ops-admin-*/
        self._discover_from_packages(result)

        # Sort by display priority
        sorted_modules = {}
        for name in self._sort_by_priority(result.modules.keys()):
            sorted_modules[name] = result.modules[name]
        result.modules = sorted_modules

        return result

    def _discover_from_scripts(self, result: ModuleDiscoveryResult) -> None:
        """Scan scripts/init_*.py and add module info."""
        scripts_dir = self.scaffold_root / "scripts"
        if not scripts_dir.exists():
            return

        for script_file in scripts_dir.glob("init_*.py"):
            module_name = script_file.stem.removeprefix("init_")
            if module_name in result.modules:
                result.modules[module_name].init_script = script_file.name
            else:
                result.modules[module_name] = ModuleInfo(
                    name=module_name,
                    init_script=script_file.name,
                )

    def _discover_from_packages(self, result: ModuleDiscoveryResult) -> None:
        """Scan packages/python/ops-admin-*/ and add package info."""
        packages_dir = self.scaffold_root / "packages" / "python"
        if not packages_dir.exists():
            return

        for pkg in packages_dir.iterdir():
            if not pkg.is_dir() or not pkg.name.startswith("ops-admin-"):
                continue

            # Package name to module name: ops-admin-ai-applications -> ai_applications
            raw_name = pkg.name.replace("ops-admin-", "", 1)
            # Convert hyphens to underscores: ai-applications -> ai_applications
            module_name = raw_name.replace("-", "_")

            src_dir = pkg / "src" / module_name

            if not src_dir.exists():
                continue

            if module_name in result.modules:
                result.modules[module_name].has_package = True
                result.modules[module_name].package_path = str(src_dir)
            else:
                result.modules[module_name] = ModuleInfo(
                    name=module_name,
                    has_package=True,
                    package_path=str(src_dir),
                )

    def _sort_by_priority(self, module_names: list[str]) -> list[str]:
        """Sort module names by display priority."""
        def sort_key(name: str) -> int:
            try:
                return self._DISPLAY_PRIORITY.index(name)
            except ValueError:
                return 999

        return sorted(module_names, key=sort_key)


# Convenience functions for easy access
_instance: ModuleDiscoveryService | None = None


def get_discovery_service(scaffold_root: Path | None = None) -> ModuleDiscoveryService:
    """Get or create the module discovery service singleton."""
    global _instance
    if _instance is None or scaffold_root is not None:
        _instance = ModuleDiscoveryService(scaffold_root)
    return _instance


def discover_modules(scaffold_root: Path | None = None) -> ModuleDiscoveryResult:
    """
    Convenience function to discover modules.

    Args:
        scaffold_root: Optional scaffold root path. Defaults to auto-detect.

    Returns:
        ModuleDiscoveryResult with all discovered modules.
    """
    service = get_discovery_service(scaffold_root)
    return service.discover()