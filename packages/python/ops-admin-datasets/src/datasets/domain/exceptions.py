from __future__ import annotations


class DatasetDomainError(Exception):
    """Base error for dataset domain validation."""


class DatasetNotFoundError(DatasetDomainError):
    """Raised when a dataset or child resource cannot be found."""


class DatasetStorageNotReadyError(DatasetDomainError):
    """Raised when dataset storage has not been explicitly initialized."""


class DatasetRuntimeUnavailableError(DatasetDomainError):
    """Raised when a dataset runtime cannot execute the requested dataset."""
