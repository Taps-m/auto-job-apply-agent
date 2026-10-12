from fastapi import APIRouter

from . import service
from .scoring import seniority_labels

router = APIRouter(prefix="/api/matching", tags=["matching"])


@router.post("/rescore")
def rescore():
    service.recompute()
    return {"ok": True}


@router.get("/seniority-levels")
def seniority_levels():
    return [{"level": k, "label": v} for k, v in sorted(seniority_labels().items())]
