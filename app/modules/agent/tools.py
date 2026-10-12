"""Backend tools exposed to Gemini (FR-411), with argument validation and approval gating (FR-413).

Tool schemas live in config/agent.json. Read-only tools run immediately; anything that
changes data becomes a pending action the user approves. No tool can submit an application.
"""
import json

from ... import config
from ...core.db import USER_ID, now, row, rows, tx
from ...core.errors import ServiceError
from ..applications import service as applications
from ..jobs import service as jobs
from ..profile import service as profile

PROFILE_FIELDS = ("preferred_name", "headline", "summary", "years_experience", "skills", "career_goals",
                  "github_url", "website_url", "notice_months")
PREFERENCE_FIELDS = ("roles", "industries", "cities", "arrangements", "min_salary_lpa", "premium_min_salary_lpa",
                     "premium_employers", "allow_unknown_salary")
EXPERIENCE_FIELDS = ("employer", "role", "start_date", "end_date", "achievements")


class ToolError(Exception):
    pass


def schemas() -> dict:
    return config.agent_config()["tools"]


def validate(name: str, args: dict) -> dict:
    spec = schemas().get(name)
    if not spec:
        raise ToolError(f"Unknown tool {name}")
    props = spec["parameters"]["properties"]
    args = dict(args or {})
    unknown = set(args) - set(props)
    if unknown:
        raise ToolError(f"Unexpected arguments: {', '.join(sorted(unknown))}")
    for req in spec["parameters"].get("required", []):
        if args.get(req) in (None, "", []):
            raise ToolError(f"Missing argument {req}")
    out = {}
    for k, v in args.items():
        t = props[k]["type"]
        try:
            if t == "integer":
                if isinstance(v, float) and not v.is_integer():
                    raise ValueError
                out[k] = int(v)
            elif t == "number":
                out[k] = float(v)
            elif t == "boolean":
                out[k] = bool(v)
            elif t == "string":
                out[k] = str(v)[:500]
            elif t == "array":
                out[k] = [int(x) for x in list(v)[:5]]
        except (TypeError, ValueError):
            raise ToolError(f"Argument {k} must be {t}")
    return out


def job_summary(j: dict) -> dict:
    m = j.get("match") or {}
    return {"job_id": j["id"], "title": j["title"], "company": j["company"], "location": j["location"],
            "work_arrangement": j["work_arrangement"], "salary_lpa": j["salary_lpa"],
            "source_url": j["source_url"], "retrieved_at": j["retrieved_at"], "listing_status": j["status"],
            "match_score": m.get("score"), "eligible": m.get("eligible"), "saved": j["saved"],
            "application": j.get("application")}


def application_summary(a: dict) -> dict:
    return {"application_id": a["id"], "job_id": a["job_id"], "job": f"{a['job']['title']} at {a['job']['company']}",
            "status": a["status"], "submitted_at": a["submitted_at"], "confirmation": a["confirmation"],
            "follow_up_on": a["follow_up_on"], "follow_up_note": a["follow_up_note"],
            "events": [{"at": e["at"], "kind": e["kind"], "detail": e["detail"]} for e in a["events"]]}


def profile_for_agent(user_id) -> dict:
    """Only approved career facts and preferences; never documents or account data."""
    b = profile.bundle(user_id)
    return {**{k: b["profile"][k] for k in PROFILE_FIELDS},
            "work_history": [{k: e[k] for k in EXPERIENCE_FIELDS} for e in b["experiences"]],
            "preferences": {k: b["preferences"][k] for k in PREFERENCE_FIELDS},
            "profile_missing": b["completeness"]["missing"]}


def _propose(tool: str, args: dict, session_id, user_id) -> dict:
    job = jobs.get_job(args["job_id"], user_id)
    with tx() as c:
        cur = c.execute("INSERT INTO agent_actions(user_id, session_id, tool, arguments, status, proposed_at)"
                        " VALUES (?,?,?,?,?,?)", (user_id, session_id, tool, json.dumps(args), "pending", now()))
    return {"pending_action_id": cur.lastrowid, "job": f"{job['title']} at {job['company']}",
            "note": "Waiting for the user to approve in the app. Nothing has changed yet."}


def _search_jobs(a, user_id, _):
    res = jobs.search(q=a.get("query", ""), location=a.get("location", ""), remote=a.get("remote", False),
                      min_salary=a.get("min_salary_lpa"), limit=max(1, min(20, a.get("limit", 10))), user_id=user_id)
    return {"interpreted": res["interpreted"], "jobs": [job_summary(j) for j in res["jobs"]]}


def _get_job_details(a, user_id, _):
    j = jobs.get_job(a["job_id"], user_id)
    return {**job_summary(j), "description": j["description"][:6000], "responsibilities": j["responsibilities"][:3000],
            "required_skills": j["required_skills"], "preferred_skills": j["preferred_skills"],
            "employment_type": j["employment_type"], "posted_at": j["posted_at"], "match": j["match"]}


def _calculate_job_match(a, user_id, _):
    from ..matching import service as matching
    matching.recompute(user_id, [a["job_id"]])
    return {"job_id": a["job_id"], **jobs.get_job(a["job_id"], user_id)["match"]}


def _compare_jobs(a, user_id, _):
    if not 2 <= len(a["job_ids"]) <= 5:
        raise ToolError("Compare between two and five jobs")
    return {"jobs": [{**job_summary(j), "match": j["match"]} for j in (jobs.get_job(i, user_id) for i in a["job_ids"])]}


def _analyze_skill_gaps(a, user_id, _):
    j = jobs.get_job(a["job_id"], user_id)
    if j["match"]["skills_gap"] is None:
        raise ToolError("The profile has no skills yet; ask the user to add them in Profile")
    return {"job_id": j["id"], "skills_gap": j["match"]["skills_gap"], "your_skills": profile_for_agent(user_id)["skills"]}


def _list_applications(a, user_id, _):
    return {"applications": [application_summary(x) for x in applications.list_all(user_id)],
            "follow_ups_due": [x["id"] for x in applications.due_follow_ups(user_id)], "today": now()[:10]}


HANDLERS = {
    "search_jobs": _search_jobs,
    "get_job_details": _get_job_details,
    "get_user_profile": lambda a, user_id, _: profile_for_agent(user_id),
    "calculate_job_match": _calculate_job_match,
    "compare_jobs": _compare_jobs,
    "analyze_skill_gaps": _analyze_skill_gaps,
    "list_applications": _list_applications,
    "get_application_status": lambda a, user_id, _: application_summary(applications.get(a["application_id"], user_id)),
    "propose_save_job": lambda a, user_id, sid: _propose("propose_save_job", a, sid, user_id),
    "propose_application_draft": lambda a, user_id, sid: _propose("propose_application_draft", a, sid, user_id),
}

# Executed only after the user approves a pending action.
APPROVED_EXECUTORS = {
    "propose_save_job": lambda args, user_id: {"saved_job_id": jobs.set_saved(args["job_id"], True, user_id)["id"]},
    "propose_application_draft": lambda args, user_id: {"application_id": applications.start(args["job_id"], user_id=user_id)["id"]},
}


def run(name: str, args: dict, session_id=None, user_id=USER_ID) -> dict:
    """Execute one validated tool call. Errors come back as data so Gemini can explain them."""
    try:
        a = validate(name, args)
        handler = HANDLERS.get(name)
        if not handler:
            raise ToolError(f"Tool {name} is not available")
        return handler(a, user_id, session_id)
    except (ToolError, ServiceError) as e:
        return {"error": str(e)}


def decide(action_id: int, approve: bool, user_id=USER_ID) -> dict:
    with tx() as c:
        act = row(c.execute("SELECT * FROM agent_actions WHERE id=? AND user_id=?", (action_id, user_id)).fetchone())
    if not act:
        raise ServiceError("Action not found", 404)
    if act["status"] != "pending":
        raise ServiceError("This action was already decided")
    result, status = {}, "rejected"
    if approve:
        try:
            result, status = APPROVED_EXECUTORS[act["tool"]](json.loads(act["arguments"]), user_id), "executed"
        except ServiceError as e:
            status, result = "failed", {"error": str(e), **e.data}
    with tx() as c:
        c.execute("UPDATE agent_actions SET status=?, result=?, decided_at=? WHERE id=?",
                  (status, json.dumps(result), now(), action_id))
    return {"id": action_id, "status": status, "result": result}


def pending(user_id=USER_ID) -> list:
    with tx() as c:
        acts = rows(c.execute("SELECT * FROM agent_actions WHERE user_id=? AND status='pending' ORDER BY id", (user_id,)))
    for a in acts:
        a["arguments"] = json.loads(a["arguments"])
    return acts
