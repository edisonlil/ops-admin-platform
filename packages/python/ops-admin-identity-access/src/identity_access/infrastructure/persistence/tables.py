from __future__ import annotations

from sqlalchemy import Boolean, Column, Integer, MetaData, String, Table, Text


metadata = MetaData()

tenants = Table(
    "tenants",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_key", String, nullable=False, unique=True),
    Column("name", String, nullable=False),
    Column("status", String, nullable=False, default="active"),
    Column("remark", Text, nullable=False, default=""),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

tenant_memberships = Table(
    "tenant_memberships",
    metadata,
    Column("tenant_id", Integer, nullable=False),
    Column("user_id", Integer, nullable=False),
    Column("is_tenant_admin", Boolean, nullable=False, default=False),
    Column("created_at", String, nullable=False),
)
