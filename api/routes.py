from __future__ import annotations

from fastapi import APIRouter

from api.ai_applications_composition import wire_ai_applications_dependencies
from api.module_registry import module_routers

wire_ai_applications_dependencies()


router = APIRouter(prefix="/api")
for module_router in module_routers():
    router.include_router(module_router)
