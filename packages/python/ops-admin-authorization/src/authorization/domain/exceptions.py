from __future__ import annotations


class AuthorizationDomainError(Exception):
    pass


class AuthorizationNotFoundError(AuthorizationDomainError):
    pass


class AuthorizationStorageNotReadyError(AuthorizationDomainError):
    pass
