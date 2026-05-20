from __future__ import annotations


class MetadataSupportError(Exception):
    """Base error for metadata support."""


class MetadataSupportValidationError(MetadataSupportError):
    """Raised when metadata support input is invalid."""


class MetadataSupportNotFoundError(MetadataSupportError):
    """Raised when metadata support data is not found."""


class MetadataSupportStorageNotReadyError(MetadataSupportError):
    """Raised when metadata support storage is not initialized."""
