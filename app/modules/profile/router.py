from fastapi import APIRouter, Body, File, UploadFile
from fastapi.responses import Response

from . import service, assets

router = APIRouter(prefix="/api", tags=["profile"])


@router.get('/profile/assets')
def profile_assets():
    return assets.get()


@router.put('/profile/links')
def professional_links(data: dict = Body(...)):
    return assets.update_links(data)


@router.post('/profile/photo')
async def upload_photo(file: UploadFile = File(...)):
    return assets.save_photo(await file.read(assets.MAX_PHOTO_BYTES + 1))


@router.get('/profile/photo')
def profile_photo():
    return Response(assets.photo(), media_type='image/png')


@router.delete('/profile/photo')
def remove_profile_photo():
    return assets.remove_photo()


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
