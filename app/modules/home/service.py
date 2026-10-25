"""M01 Home dashboard: only what is needed to decide the next step."""
from ... import config
from ...core.db import USER_ID
from ..agent import gemini
from ..applications import service as applications
from ..jobs import service as jobs
from ..profile import service as profile

TOP_MATCHES = 3


def overview(b: dict, user_id=USER_ID) -> dict:
    p, prefs = b["profile"], b["preferences"]
    found = jobs.search(user_id=user_id)["jobs"]
    return {"headline": p["headline"], "years_experience": p["years_experience"],
            "current_role": (b["experiences"][0]["role"] + " at " + b["experiences"][0]["employer"]) if b["experiences"] else "",
            "target_roles": prefs["roles"], "top_cities": prefs["cities"][:3],
            "min_salary_lpa": prefs["min_salary_lpa"], "tracked_jobs": len(found),
            "eligible_jobs": sum(1 for j in found if (j["match"] or {}).get("eligible")),
            "saved_jobs": sum(1 for j in found if j["saved"]),
            "applied_jobs": applications.metrics(user_id)["submitted"]}


def summary(user_id=USER_ID) -> dict:
    b = profile.bundle(user_id)
    return {"version": config.app_config()["version"], "preferred_name": b["profile"]["preferred_name"],
            "overview": overview(b, user_id),
            "top_matches": jobs.top_matches(TOP_MATCHES, user_id), "metrics": applications.metrics(user_id),
            "follow_ups_due": len(applications.due_follow_ups(user_id)), "completeness": b["completeness"],
            "gemini_connected": gemini.connected()}
