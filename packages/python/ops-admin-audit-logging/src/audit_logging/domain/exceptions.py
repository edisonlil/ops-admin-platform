from __future__ import annotations


class AuditLoggingError(Exception):
    """Base audit logging domain error."""


class AuditLoggingNotFound(AuditLoggingError):
    """Requested audit logging resource does not exist."""


class AuditLoggingStorageNotReady(AuditLoggingError):
    """Audit logging tables have not been initialized."""
