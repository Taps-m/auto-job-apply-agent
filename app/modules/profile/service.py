"""M07 User profile & preferences."""
import json
from urllib.parse import urlparse

from ... import config
from ...core.db import USER_ID, now, row, rows, tx
from ...core.errors import ServiceError
from ...core.text import clean_list, text
from ..matching.scoring import seniority_labels

ARRANGEMENTS = ("remote", "hybrid", "on-site")
SEARCH_FREQUENCIES = ("manual", "daily", "weekly")
AUTOMATION_LEVELS = ("manual", "assisted", "approved_automation")
LIST_PREFERENCES = ("roles", "industries", "cities", "premium_employers", "excluded_companies",
                    "excluded_locations", "excluded_keywords")


def get_preferences(c, user_id=USER_ID) -> dict:
    r = c.execute("SELECT data FROM job_preferences WHERE user_id=?", (user_id,)).fetchone()
    defaults = config.default_preferences()
    return {**defaults, **json.loads(r["data"])} if r else dict(defaults)


def get_profile(c, user_id=USER_ID) -> dict:
    p = row(c.execute("SELECT * FROM career_profiles WHERE user_id=?", (user_id,)).fetchone()) or {}
    u = row(c.execute("SELECT preferred_name FROM users WHERE id=?", (user_id,)).fetchone()) or {}
    p["skills"] = json.loads(p.get("skills") or "[]")
    p["preferred_name"] = u.get("preferred_name", "")
    return p


def get_experiences(c, user_id=USER_ID) -> list:
    return rows(c.execute("SELECT * FROM work_experiences WHERE user_id=? ORDER BY start_date DESC, id DESC",
                          (user_id,)))


def completeness(profile: dict, experiences: list, prefs: dict, has_resume: bool) -> dict:
    """FR-710: what is missing for better matching."""
    checks = [
        ("Preferred name", bool(profile.get("preferred_name"))),
        ("Headline", bool(profile.get("headline"))),
        ("Years of experience", profile.get("years_experience") is not None),
        ("Skills (at least 5)", len(profile.get("skills", [])) >= 5),
        ("Work history", bool(experiences)),
        ("Career goals", bool(profile.get("career_goals"))),
        ("Master resume uploaded", has_resume),
        ("Target roles", bool(prefs.get("roles"))),
        ("Preferred cities", bool(prefs.get("cities"))),
        ("Notice period", profile.get("notice_months") is not None),
    ]
    done = sum(ok for _, ok in checks)
    return {"percent": round(done / len(checks) * 100), "missing": [n for n, ok in checks if not ok]}


def bundle(user_id=USER_ID) -> dict:
    with tx() as c:
        profile, prefs = get_profile(c, user_id), get_preferences(c, user_id)
        exps = get_experiences(c, user_id)
        has_resume = c.execute("SELECT 1 FROM documents WHERE user_id=? AND kind='resume' AND is_master=1",
                               (user_id,)).fetchone() is not None
    return {"profile": profile, "experiences": exps, "preferences": prefs,
            "completeness": completeness(profile, exps, prefs, has_resume)}


def _rescore(user_id) -> None:
    from ..matching import service as matching  # Imported late: matching reads profiles.
    matching.recompute(user_id)


def update_profile(data: dict, user_id=USER_ID) -> dict:
    years = data.get("years_experience")
    if years in ("", None):
        years = None
    else:
        years = float(years)
        if not 0 <= years <= 60:
            raise ServiceError("Years of experience must be between 0 and 60")
    notice = data.get("notice_months")
    notice = None if notice in ("", None) else int(notice)
    for key in ("github_url", "website_url"):
        if data.get(key) and urlparse(str(data[key])).scheme not in ("http", "https"):
            raise ServiceError(f"{key} must be an http(s) link")
    with tx() as c:
        c.execute("UPDATE users SET preferred_name=? WHERE id=?", (text(data.get("preferred_name"), 60), user_id))
        c.execute(
            "UPDATE career_profiles SET headline=?, summary=?, years_experience=?, skills=?, career_goals=?,"
            " github_url=?, website_url=?, notice_months=?, work_authorization=?, updated_at=? WHERE user_id=?",
            (text(data.get("headline"), 200), text(data.get("summary"), 4000), years,
             json.dumps(clean_list(data.get("skills"))), text(data.get("career_goals"), 2000),
             text(data.get("github_url"), 300), text(data.get("website_url"), 300), notice,
             text(data.get("work_authorization"), 200), now(), user_id))
    _rescore(user_id)
    return bundle(user_id)


def add_experience(data: dict, user_id=USER_ID) -> dict:
    employer, role = text(data.get("employer"), 120), text(data.get("role"), 120)
    if not employer or not role:
        raise ServiceError("Employer and role are required")
    with tx() as c:
        c.execute("INSERT INTO work_experiences(user_id, employer, role, start_date, end_date, achievements)"
                  " VALUES (?,?,?,?,?,?)",
                  (user_id, employer, role, text(data.get("start_date"), 20), text(data.get("end_date"), 20),
                   text(data.get("achievements"), 4000)))
    return bundle(user_id)


def delete_experience(exp_id: int, user_id=USER_ID) -> dict:
    with tx() as c:
        c.execute("DELETE FROM work_experiences WHERE id=? AND user_id=?", (exp_id, user_id))
    return bundle(user_id)


def update_preferences(data: dict, user_id=USER_ID) -> dict:
    with tx() as c:
        prefs = get_preferences(c, user_id)
    for key in LIST_PREFERENCES:
        if key in data:
            prefs[key] = clean_list(data[key])
    if "arrangements" in data:
        arr = [a.lower() for a in clean_list(data["arrangements"])]
        if any(a not in ARRANGEMENTS for a in arr):
            raise ServiceError(f"Arrangements must be {', '.join(ARRANGEMENTS)}")
        prefs["arrangements"] = arr
    for key in ("min_salary_lpa", "premium_min_salary_lpa"):
        if key in data:
            v = float(data[key])
            if not 0 <= v <= 1000:
                raise ServiceError(f"{key} must be between 0 and 1000")
            prefs[key] = v
    if "allow_unknown_salary" in data:
        prefs["allow_unknown_salary"] = bool(data["allow_unknown_salary"])
    labels = seniority_labels()
    for key in ("seniority_min", "seniority_max"):
        if key in data:
            v = int(data[key])
            if v not in labels:
                raise ServiceError(f"{key} must be {min(labels)}–{max(labels)}")
            prefs[key] = v
    if prefs["seniority_min"] > prefs["seniority_max"]:
        raise ServiceError("Minimum seniority cannot exceed maximum seniority")
    if "weights" in data:
        names = config.default_preferences()["weights"]
        w = {k: float(data["weights"].get(k, prefs["weights"].get(k, 0))) for k in names}
        if any(v < 0 or v > 100 for v in w.values()) or sum(w.values()) <= 0:
            raise ServiceError("Weights must be 0–100 and not all zero")
        prefs["weights"] = w
    if "search_frequency" in data:
        if data["search_frequency"] not in SEARCH_FREQUENCIES:
            raise ServiceError(f"Search frequency must be {', '.join(SEARCH_FREQUENCIES)}")
        prefs["search_frequency"] = data["search_frequency"]
    if "automation_level" in data:
        if data["automation_level"] not in AUTOMATION_LEVELS:
            raise ServiceError("Invalid automation level")
        prefs["automation_level"] = data["automation_level"]
    # Keep keywords for roles that have them; a new role matches on its own name.
    prefs["role_keywords"] = {r: prefs.get("role_keywords", {}).get(r, [r]) for r in prefs["roles"]}
    with tx() as c:
        c.execute("UPDATE job_preferences SET data=?, updated_at=? WHERE user_id=?",
                  (json.dumps(prefs), now(), user_id))
    _rescore(user_id)
    return bundle(user_id)
