from fastapi import APIRouter

from . import service

router = APIRouter(prefix="/api", tags=["home"])


@router.get("/home")
def home():
    return service.summary()
