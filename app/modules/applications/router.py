from fastapi import APIRouter, Body

from . import service
from . import analytics

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get('/progress')
def application_progress():
    return analytics.progress()


@router.get("")
def applications():
    return {"applications": service.list_all(), "metrics": service.metrics(),
            "follow_ups_due": [a["id"] for a in service.due_follow_ups()]}


@router.post("")
def start(data: dict = Body(...)):
    return service.start(int(data["job_id"]), bool(data.get("force")))


@router.get("/{app_id}")
def application(app_id: int):
    return service.get(app_id)


@router.put("/{app_id}")
def update(app_id: int, data: dict = Body(...)):
    return service.update_draft(app_id, data)


@router.post("/{app_id}/approve")
def approve(app_id: int):
    return service.approve(app_id)


@router.post("/{app_id}/withdraw-approval")
def withdraw_approval(app_id: int):
    return service.withdraw_approval(app_id)


@router.post("/{app_id}/open")
def open_employer_page(app_id: int):
    return service.open_employer_page(app_id)


@router.post("/{app_id}/confirm")
def confirm(app_id: int, data: dict = Body(...)):
    return service.confirm_submitted(app_id, data.get("confirmation", ""))


@router.post("/{app_id}/outcome")
def outcome(app_id: int, data: dict = Body(...)):
    return service.set_outcome(app_id, data.get("status", ""), data.get("note", ""))


@router.put("/{app_id}/follow-up")
def follow_up(app_id: int, data: dict = Body(...)):
    return service.set_follow_up(app_id, data.get("follow_up_on") or "", data.get("follow_up_note") or "")
