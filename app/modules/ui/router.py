"""Serves the single-page interface from app/static."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ...core.errors import ServiceError

STATIC = Path(__file__).resolve().parents[2] / "static"
router = APIRouter(tags=["ui"])


@router.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@router.get("/static/{name}", include_in_schema=False)
def static(name: str):
    path = (STATIC / name).resolve()
    if path.parent != STATIC or not path.is_file():
        raise ServiceError("Not found", 404)
    return FileResponse(path)
