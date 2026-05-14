from __future__ import annotations


class OrganizationDomainError(Exception):
    pass


class OrganizationNotFoundError(OrganizationDomainError):
    pass


class OrganizationStorageNotReadyError(OrganizationDomainError):
    pass
