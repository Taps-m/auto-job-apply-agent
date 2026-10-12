"""Local-only access rules and error mapping, applied to every module's routes."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .. import config
from .errors import ServiceError


def install(app: FastAPI) -> None:
    cfg = config.app_config()
    allowed = cfg["allowed_hosts"]

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        # Block DNS rebinding and cross-site requests: this app holds personal data and must stay local.
        if request.headers.get("host") not in allowed:
            return JSONResponse({"error": "Invalid host"}, 403)
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD") and origin and origin.removeprefix("http://") not in allowed:
            return JSONResponse({"error": "Invalid origin"}, 403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = cfg["content_security_policy"]
        return response

    @app.exception_handler(ServiceError)
    async def service_error(_, e: ServiceError):
        return JSONResponse({"error": str(e), **e.data}, e.status)

    @app.exception_handler(ValueError)
    async def value_error(_, e: ValueError):
        return JSONResponse({"error": f"Invalid value: {e}"}, 400)
