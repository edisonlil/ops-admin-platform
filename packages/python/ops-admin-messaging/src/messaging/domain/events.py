from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MessageDispatched:
    tenant_id: int
    message_id: int
    recipient_count: int
