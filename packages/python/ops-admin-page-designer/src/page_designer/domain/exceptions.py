from __future__ import annotations


class PageDesignerDomainError(ValueError):
    """Raised when a page designer business rule is violated."""


class PageDesignerNotFoundError(LookupError):
    """Raised when a page definition or version cannot be found."""


class PageDesignerStorageNotReadyError(RuntimeError):
    """Raised when page designer storage has not been initialized."""
