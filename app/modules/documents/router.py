from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse

from . import service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
def documents():
    return service.list_all()


@router.post("")
async def upload(file: UploadFile = File(...), is_master: bool = Form(True), kind: str = Form("resume")):
    content = await file.read(service.max_upload_bytes() + 1)
    return service.save(file.filename or kind, content, is_master, kind=kind)


@router.post("/{doc_id}/master")
def make_master(doc_id: int):
    return service.set_master(doc_id)


@router.get("/{doc_id}/file")
def download(doc_id: int):
    d = service.get(doc_id)
    return FileResponse(service.path_of(d), filename=d["filename"])
