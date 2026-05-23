from __future__ import annotations

from typing import Any, Protocol


class AICapabilitiesRepository(Protocol):
    def __getattr__(self, name: str) -> Any: ...
    def require_ai_capabilities_schema(self, *args: Any, **kwargs: Any) -> Any: ...

