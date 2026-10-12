from fastapi import APIRouter, Body

from . import service

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/profile")
def profile():
    return service.bundle()


@router.put("/profile")
def update_profile(data: dict = Body(...)):
    return service.update_profile(data)


@router.post("/profile/experiences")
def add_experience(data: dict = Body(...)):
    return service.add_experience(data)


@router.delete("/profile/experiences/{exp_id}")
def delete_experience(exp_id: int):
    return service.delete_experience(exp_id)


@router.put("/preferences")
def update_preferences(data: dict = Body(...)):
    return service.update_preferences(data)
