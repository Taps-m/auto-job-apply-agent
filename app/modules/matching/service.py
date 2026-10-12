"""M03 fit analysis: stores a score per job for the user and recalculates it when inputs change."""
import json

from ...core.db import USER_ID, now, rows, tx
from ..profile.service import get_preferences, get_profile
from .scoring import score_job


def decode_job(j: dict) -> dict:
    j["required_skills"] = json.loads(j.get("required_skills") or "[]")
    j["preferred_skills"] = json.loads(j.get("preferred_skills") or "[]")
    return j


def recompute(user_id=USER_ID, job_ids=None) -> None:
    with tx() as c:
        profile, prefs = get_profile(c, user_id), get_preferences(c, user_id)
        sql, args = "SELECT * FROM job_postings", ()
        if job_ids:
            sql += f" WHERE id IN ({','.join('?' for _ in job_ids)})"
            args = tuple(job_ids)
        for j in rows(c.execute(sql, args)):
            m = score_job(decode_job(j), profile, prefs)
            c.execute("INSERT INTO job_matches(job_id, user_id, score, breakdown, calculated_at) VALUES (?,?,?,?,?)"
                      " ON CONFLICT(job_id, user_id) DO UPDATE SET score=excluded.score,"
                      " breakdown=excluded.breakdown, calculated_at=excluded.calculated_at",
                      (j["id"], user_id, m["score"], json.dumps(m), now()))


def get_match(c, job_id: int, user_id=USER_ID):
    m = c.execute("SELECT breakdown FROM job_matches WHERE job_id=? AND user_id=?", (job_id, user_id)).fetchone()
    return json.loads(m["breakdown"]) if m else None
