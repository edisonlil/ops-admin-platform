from __future__ import annotations


class CronDomainError(ValueError):
    """Raised when cron domain invariants are violated."""


class CronNotFoundError(LookupError):
    """Raised when a cron resource cannot be found."""


class CronStorageNotReadyError(RuntimeError):
    """Raised when cron persistence has not been explicitly initialized."""
