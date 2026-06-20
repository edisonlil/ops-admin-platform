from __future__ import annotations

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.config import admin_dist_path, cors_origins
from api.errors import http_exception_handler, request_validation_exception_handler
from api.routes import router
from system.interfaces.http import RequestContextMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="ops-admin-platform API", version="0.1.0")
    add_audit_logging(app)
    app.add_middleware(RequestContextMiddleware)
    allowed_origins = cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allowed_origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.include_router(router)
    mount_admin(app)
    return app


def add_audit_logging(app: FastAPI) -> None:
    try:
        from audit_logging.application import dispatcher
        from audit_logging.interfaces.http.middleware import AuditHttpLoggingMiddleware
    except Exception:
        return
    app.add_middleware(AuditHttpLoggingMiddleware)

    @app.on_event("startup")
    def start_audit_logging() -> None:
        dispatcher.start_worker()
        dispatcher.record_system_log(
            {
                "tenant_id": 0,
                "event_action": "audit.worker.start",
                "event_outcome": "success",
                "severity": "info",
                "source_module": "audit_logging",
                "summary": "审计日志后台写入任务已启动",
            }
        )

    @app.on_event("shutdown")
    def stop_audit_logging() -> None:
        dispatcher.record_system_log(
            {
                "tenant_id": 0,
                "event_action": "audit.worker.stop",
                "event_outcome": "success",
                "severity": "info",
                "source_module": "audit_logging",
                "summary": "审计日志后台写入任务已停止",
            }
        )
        dispatcher.stop_worker()


def mount_admin(app: FastAPI) -> None:
    dist_path = admin_dist_path()
    assets_path = dist_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="admin-assets")

    config_path = dist_path / "app.config.js"
    if config_path.exists():
        @app.get("/app.config.js", include_in_schema=False)
        def admin_config() -> FileResponse:
            return FileResponse(config_path, media_type="application/javascript")

    index_path = dist_path / "index.html"
    if index_path.exists():
        @app.get("/")
        def admin_index() -> FileResponse:
            return FileResponse(index_path)

        @app.get("/{path:path}", include_in_schema=False)
        def admin_fallback(path: str) -> FileResponse:
            return FileResponse(index_path)


app = create_app()
