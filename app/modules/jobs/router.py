from fastapi import APIRouter, Body

from . import service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
def search(q: str = "", location: str = "", remote: bool = False, min_salary: float | None = None,
           company: str = "", exclude_company: str = "", seniority: str = "", saved_only: bool = False,
           include_ineligible: bool = True):
    return service.search(q, location, remote, min_salary, company, exclude_company, seniority,
                          saved_only, include_ineligible)


@router.post("")
def add_job(data: dict = Body(...)):
    return service.add_job(data)


@router.get("/{job_id}")
def job(job_id: int):
    return service.get_job(job_id)


@router.delete("/{job_id}")
def delete_job(job_id: int):
    service.delete_job(job_id)
    return {"ok": True}


@router.post("/{job_id}/save")
def save_job(job_id: int, data: dict = Body({"saved": True})):
    return service.set_saved(job_id, bool(data.get("saved", True)))


@router.post("/{job_id}/check")
def check_job(job_id: int):
    return service.check_status(job_id)
