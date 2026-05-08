from __future__ import annotations

from fastapi import APIRouter

from api.module_registry import module_routers


router = APIRouter(prefix="/api")
for module_router in module_routers():
    router.include_router(module_router)
