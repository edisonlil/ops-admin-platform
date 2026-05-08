from __future__ import annotations

from fastapi import APIRouter

from appearance.interfaces.http.router import router as appearance_router
from identity_access.interfaces.http.router import router as identity_access_router
from llm_runtime.interfaces.http.router import router as llm_runtime_router
from system.interfaces.router import router as system_router


router = APIRouter(prefix="/api")
router.include_router(system_router)
router.include_router(identity_access_router)
router.include_router(llm_runtime_router)
router.include_router(appearance_router)
