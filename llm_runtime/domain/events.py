from __future__ import annotations

from system.domain.events import DomainEvent


def llm_runtime_settings_updated(provider: str, enabled: bool, *, correlation_id: str | None = None) -> DomainEvent:
    return DomainEvent(
        event_type="llm_runtime.settings_updated",
        source="llm_runtime",
        payload={"provider": provider, "enabled": enabled},
        correlation_id=correlation_id,
    )
