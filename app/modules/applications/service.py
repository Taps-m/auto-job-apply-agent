"""M05 Application management: draft → readiness → approval → employer page → confirmed submission → outcome."""
import json

from ...core.db import USER_ID, now, row, rows, tx
from ...core.errors import ServiceError
from ...core.text import text
from ..documents import service as documents
from ..jobs import service as jobs
from ..profile.service import get_profile

STATUSES = ("draft", "approved", "awaiting_confirmation", "submitted", "interview", "offer", "rejected", "withdrawn")
ACTIVE = ("draft", "approved", "awaiting_confirmation", "submitted", "interview", "offer")
SUBMITTED_OR_LATER = ("submitted", "interview", "offer", "rejected")
RESPONDED = ("interview", "offer", "rejected")
OUTCOMES = ("interview", "offer", "rejected", "withdrawn")


def _event(c, app_id: int, kind: str, detail: str = "") -> None:
    c.execute("INSERT INTO application_events(application_id, at, kind, detail) VALUES (?,?,?,?)",
              (app_id, now(), kind, detail[:2000]))


def _update(c, app_id: int, **fields) -> None:
    fields["updated_at"] = now()
    c.execute(f"UPDATE applications SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?", (*fields.values(), app_id))


def readiness(app: dict, user_id=USER_ID) -> dict:
    """FR-502: documents and mandatory information present before approval."""
    with tx() as c:
        profile = get_profile(c, user_id)
    checks = [
        {"item": "Resume attached", "ok": app.get("resume_document_id") is not None},
        {"item": "Preferred name in profile", "ok": bool(profile.get("preferred_name"))},
        {"item": "Notice period in profile", "ok": profile.get("notice_months") is not None},
        {"item": "Employer application link", "ok": bool(app["job"]["source_url"])},
        {"item": "Vacancy not marked expired", "ok": app["job"]["status"] != "expired"},
    ]
    warnings = list((app["job"].get("match") or {}).get("blockers", []))
    if app["job"]["status"] in ("unverified", "inaccessible"):
        warnings.append("The vacancy link could not be verified recently")
    return {"ready": all(ch["ok"] for ch in checks), "checks": checks, "warnings": warnings}


def get(app_id: int, user_id=USER_ID) -> dict:
    with tx() as c:
        a = row(c.execute("SELECT * FROM applications WHERE id=? AND user_id=?", (app_id, user_id)).fetchone())
        if not a:
            raise ServiceError("Application not found", 404)
        a["answers"] = json.loads(a["answers"] or "{}")
        a["events"] = rows(c.execute("SELECT * FROM application_events WHERE application_id=? ORDER BY id", (app_id,)))
        job = row(c.execute("SELECT * FROM job_postings WHERE id=?", (a["job_id"],)).fetchone())
        a["job"] = jobs.with_match(c, job, user_id)
        a["resume"] = row(c.execute("SELECT id, filename FROM documents WHERE id=? AND user_id=?",
                                    (a["resume_document_id"], user_id)).fetchone())
    a["readiness"] = readiness(a, user_id)
    return a


def list_all(user_id=USER_ID) -> list:
    with tx() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM applications WHERE user_id=? ORDER BY updated_at DESC",
                                          (user_id,))]
    return [get(i, user_id) for i in ids]


def start(job_id: int, force: bool = False, user_id=USER_ID) -> dict:
    jobs.get_job(job_id, user_id)
    with tx() as c:
        existing = c.execute(
            f"SELECT id, status FROM applications WHERE job_id=? AND user_id=? AND status IN ({','.join('?' * len(ACTIVE))})",
            (job_id, user_id, *ACTIVE)).fetchone()
        if existing and not force:  # FR-508
            raise ServiceError(f"You already have an application for this job ({existing['status']})", 409,
                               {"application_id": existing["id"]})
        t = now()
        cur = c.execute("INSERT INTO applications(user_id, job_id, status, resume_document_id, created_at, updated_at)"
                        " VALUES (?,?,?,?,?,?)", (user_id, job_id, "draft", documents.master_resume_id(user_id), t, t))
        _event(c, cur.lastrowid, "created", "Draft started")
    return get(cur.lastrowid, user_id)


def update_draft(app_id: int, data: dict, user_id=USER_ID) -> dict:
    a = get(app_id, user_id)
    if a["status"] != "draft":
        raise ServiceError("Only drafts can be edited; withdraw approval if you need to change it")
    fields = {}
    if "cover_letter" in data:
        fields["cover_letter"] = text(data["cover_letter"], 10000)
    if "answers" in data:
        if not isinstance(data["answers"], dict):
            raise ServiceError("Answers must be question/answer pairs")
        fields["answers"] = json.dumps({text(k, 300): text(v, 2000) for k, v in data["answers"].items() if text(k, 300)})
    if "resume_document_id" in data:
        doc = data["resume_document_id"]
        if doc is not None:
            documents.get(int(doc), user_id)
        fields["resume_document_id"] = doc
    with tx() as c:
        _update(c, app_id, **fields)
        _event(c, app_id, "edited", ", ".join(fields))
    return get(app_id, user_id)


def approve(app_id: int, user_id=USER_ID) -> dict:
    """FR-504 explicit authorization. Reached only from the user's own click, never by the agent."""
    a = get(app_id, user_id)
    if a["status"] != "draft":
        raise ServiceError("Only a draft can be approved")
    if not a["readiness"]["ready"]:
        missing = [ch["item"] for ch in a["readiness"]["checks"] if not ch["ok"]]
        raise ServiceError("Not ready: " + ", ".join(missing), 422)
    with tx() as c:
        _update(c, app_id, status="approved", approved_at=now())
        _event(c, app_id, "approved", "You approved this application for submission")
    return get(app_id, user_id)


def withdraw_approval(app_id: int, user_id=USER_ID) -> dict:
    a = get(app_id, user_id)
    if a["status"] not in ("approved", "awaiting_confirmation"):
        raise ServiceError("Nothing to withdraw")
    with tx() as c:
        _update(c, app_id, status="draft", approved_at=None)
        _event(c, app_id, "approval_withdrawn", "Back to draft for editing")
    return get(app_id, user_id)


def open_employer_page(app_id: int, user_id=USER_ID) -> dict:
    """FR-505. Opening the page is recorded but never counts as a submission."""
    a = get(app_id, user_id)
    if a["status"] not in ("approved", "awaiting_confirmation"):
        raise ServiceError("Approve the application before opening the employer's page")
    with tx() as c:
        _update(c, app_id, status="awaiting_confirmation", opened_external_at=now())
        _event(c, app_id, "opened_employer_page",
               "Employer page opened. This is not a submission; confirm once the employer accepts it.")
    return {"url": a["job"]["source_url"], "application": get(app_id, user_id)}


def confirm_submitted(app_id: int, confirmation: str, user_id=USER_ID) -> dict:
    """FR-510: submitted only with a confirmation from the employer or the user."""
    a = get(app_id, user_id)
    if a["status"] not in ("approved", "awaiting_confirmation"):
        raise ServiceError("Only an approved application can be confirmed as submitted")
    confirmation = text(confirmation, 500)
    if not confirmation:
        raise ServiceError("Enter the confirmation you received (reference number, email subject, or 'manual')")
    with tx() as c:
        _update(c, app_id, status="submitted", submitted_at=now(), confirmation=confirmation)
        _event(c, app_id, "submitted", f"Confirmed: {confirmation}")
        from .analytics import snapshot
        snapshot(c, app_id, (a['job'].get('match') or {}).get('score'))
    return get(app_id, user_id)


def set_outcome(app_id: int, status: str, note: str = "", user_id=USER_ID) -> dict:
    a = get(app_id, user_id)
    if status not in OUTCOMES:
        raise ServiceError(f"Outcome must be {', '.join(OUTCOMES)}")
    if status != "withdrawn" and not a["submitted_at"]:
        raise ServiceError("Record a confirmed submission before recording an outcome")
    with tx() as c:
        _update(c, app_id, status=status)
        _event(c, app_id, status, text(note, 2000))
    return get(app_id, user_id)


def set_follow_up(app_id: int, on: str, note: str, user_id=USER_ID) -> dict:
    """FR-509"""
    get(app_id, user_id)
    with tx() as c:
        _update(c, app_id, follow_up_on=text(on, 10) or None, follow_up_note=text(note, 500))
        _event(c, app_id, "follow_up_set", f"{on or 'cleared'} {note or ''}".strip())
    return get(app_id, user_id)


def due_follow_ups(user_id=USER_ID) -> list:
    today = now()[:10]
    return [a for a in list_all(user_id) if a["follow_up_on"] and a["follow_up_on"] <= today and a["status"] in ACTIVE]


def metrics(user_id=USER_ID) -> dict:
    with tx() as c:
        counts = {r["status"]: r["n"] for r in c.execute(
            "SELECT status, COUNT(*) n FROM applications WHERE user_id=? GROUP BY status", (user_id,))}
    submitted = sum(counts.get(s, 0) for s in SUBMITTED_OR_LATER)
    responded = sum(counts.get(s, 0) for s in RESPONDED)
    return {"by_status": counts, "submitted": submitted,
            "interviews": counts.get("interview", 0) + counts.get("offer", 0),
            "response_rate": round(responded / submitted * 100) if submitted else None}
