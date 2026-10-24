from contextlib import asynccontextmanager
from fastapi import APIRouter
from . import service


@asynccontextmanager
async def lifespan(app):
    service.startup()
    yield
    service.shutdown()


router = APIRouter(prefix="/api/discovery", tags=["discovery"], lifespan=lifespan)


@router.get("")
def status():
    return service.status()


@router.post("/run", status_code=202)
def run():
    return service.start()
