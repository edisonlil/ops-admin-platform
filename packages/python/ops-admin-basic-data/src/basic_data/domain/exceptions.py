from __future__ import annotations


class BasicDataDomainError(ValueError):
    """Raised when basic data domain invariants are violated."""


class BasicDataNotFoundError(LookupError):
    """Raised when a basic data resource cannot be found."""


class BasicDataStorageNotReadyError(RuntimeError):
    """Raised when basic data persistence has not been explicitly initialized."""
