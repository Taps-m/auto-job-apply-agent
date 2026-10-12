from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from ..agent import gemini
from . import service

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
def settings():
    return service.current()


@router.put("/settings")
def update(data: dict = Body(...)):
    return service.update(data)


@router.get("/settings/models")
def models():
    try:
        return {"models": service.models()}
    except Exception as e:  # Report Gemini errors to the UI instead of failing the page.
        return JSONResponse({"error": gemini.friendly_error(e), "models": []}, 502)


@router.post("/privacy/delete-all")
def delete_all(data: dict = Body(...)):
    service.delete_all_data(data.get("confirm", ""))
    return {"ok": True}
