"""M01 Home dashboard: only what is needed to decide the next step."""
from ... import config
from ...core.db import USER_ID
from ..agent import gemini
from ..applications import service as applications
from ..jobs import service as jobs
from ..profile import service as profile

TOP_MATCHES = 3


def summary(user_id=USER_ID) -> dict:
    b = profile.bundle(user_id)
    return {"version": config.app_config()["version"], "preferred_name": b["profile"]["preferred_name"],
            "top_matches": jobs.top_matches(TOP_MATCHES, user_id), "metrics": applications.metrics(user_id),
            "follow_ups_due": len(applications.due_follow_ups(user_id)), "completeness": b["completeness"],
            "gemini_connected": gemini.connected()}
