"""M02 Job search & matches: vacancy records, duplicate merging, search, shortlist and link checks."""
import json
import re
from urllib.parse import urlparse

import httpx

from ... import config
from ...core.db import USER_ID, now, row, rows, tx
from ...core.errors import ServiceError
from ...core.text import clean_list, text
from ..matching import service as matching
from ..profile.service import ARRANGEMENTS

COMPANY_NOISE = r"\b(pvt|private|ltd|limited|inc|llp|llc|india|technologies|services)\b"


def dedupe_key(company: str, title: str, location: str) -> str:
    def norm(s):
        s = re.sub(COMPANY_NOISE, "", s.lower())
        return re.sub(r"[^a-z0-9]+", " ", s).strip()
    return f"{norm(company)}|{norm(title)}|{norm(location.split(',')[0] if location else '')}"


def with_match(c, j: dict, user_id=USER_ID) -> dict:
    from ..discovery.service import ensure
    ensure(c)
    j = matching.decode_job(j)
    j["discovery"] = row(c.execute("SELECT guid,expires_at,salary_text FROM discovered_jobs WHERE job_id=?", (j["id"],)).fetchone())
    j["match"] = matching.get_match(c, j["id"], user_id)
    j["saved"] = c.execute("SELECT 1 FROM saved_jobs WHERE job_id=? AND user_id=?",
                           (j["id"], user_id)).fetchone() is not None
    j["application"] = row(c.execute("SELECT id, status FROM applications WHERE job_id=? AND user_id=?"
                                     " ORDER BY id DESC LIMIT 1", (j["id"], user_id)).fetchone())
    return j


def add_job(data: dict, user_id=USER_ID) -> dict:
    title, company = text(data.get("title"), 200), text(data.get("company"), 200)
    url = text(data.get("source_url"), 1000)
    if not title or not company:
        raise ServiceError("Job title and company are required")
    if urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc:
        raise ServiceError("A source link (http or https) is required for every job")
    salary = data.get("salary_lpa")
    salary = None if salary in ("", None) else float(salary)
    if salary is not None and not 0 <= salary <= 10000:
        raise ServiceError("Salary must be a positive number in LPA")
    location = text(data.get("location"), 200)
    arrangement = text(data.get("work_arrangement"), 40).lower()
    if arrangement and arrangement not in ARRANGEMENTS:
        raise ServiceError(f"Work arrangement must be {', '.join(ARRANGEMENTS)}")
    key = dedupe_key(company, title, location)
    fields = {
        "title": title, "company": company, "location": location, "work_arrangement": arrangement,
        "employment_type": text(data.get("employment_type"), 40), "salary_lpa": salary,
        "description": text(data.get("description"), 20000),
        "responsibilities": text(data.get("responsibilities"), 10000),
        "required_skills": json.dumps(clean_list(data.get("required_skills"))),
        "preferred_skills": json.dumps(clean_list(data.get("preferred_skills"))),
        "source_name": text(data.get("source_name"), 80) or urlparse(url).netloc,
        "source_url": url, "posted_at": text(data.get("posted_at"), 40) or None,
    }
    with tx() as c:
        same_url = c.execute("SELECT id FROM job_postings WHERE source_url=?", (url,)).fetchone()
        if same_url:
            raise ServiceError("This job link is already saved", 409, {"job_id": same_url["id"]})
        existing = row(c.execute("SELECT * FROM job_postings WHERE dedupe_key=?", (key,)).fetchone())
        if existing:
            # Same vacancy from another source: fill gaps only, never overwrite recorded facts (FR-208).
            updates = {k: v for k, v in fields.items() if k not in ("source_url", "source_name")
                       and v not in (None, "", "[]") and existing.get(k) in (None, "", "[]")}
            if updates:
                c.execute(f"UPDATE job_postings SET {', '.join(f'{k}=?' for k in updates)} WHERE id=?",
                          (*updates.values(), existing["id"]))
            job_id, merged = existing["id"], True
        else:
            cur = c.execute(
                f"INSERT INTO job_postings({', '.join(fields)}, dedupe_key, retrieved_at)"
                f" VALUES ({', '.join('?' for _ in fields)}, ?, ?)", (*fields.values(), key, now()))
            job_id, merged = cur.lastrowid, False
    matching.recompute(user_id, [job_id])
    return {"job": get_job(job_id, user_id), "merged_with_existing": merged}


def get_job(job_id: int, user_id=USER_ID) -> dict:
    with tx() as c:
        from ..discovery.service import expire
        expire(c)
        j = row(c.execute("SELECT * FROM job_postings WHERE id=?", (job_id,)).fetchone())
        if not j:
            raise ServiceError("Job not found", 404)
        return with_match(c, j, user_id)


def parse_natural_query(q: str) -> dict:
    """Rule-based interpreter for searches like 'credit risk jobs in Kolkata above 30 LPA' (FR-201)."""
    q = (q or "").strip()
    filters = {}
    m = re.search(r"\b(?:above|over|min(?:imum)?|at least|>=?)\s*₹?\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|l)?\b", q, re.I)
    if m:
        filters["min_salary"] = float(m.group(1))
        q = q.replace(m.group(0), " ")
    if re.search(r"\bremote\b", q, re.I):
        filters["remote"] = True
        q = re.sub(r"\bremote\b", " ", q, flags=re.I)
    m = re.search(r"\b(?:in|at|near)\s+([a-z][a-z .]+?)\s*$", q.strip(), re.I)
    if m:
        filters["location"] = m.group(1).strip()
        q = q.strip()[: m.start()]
    q = re.sub(r"\b(jobs?|roles?|positions?|openings?|vacanc(?:y|ies)|find|show|me|for)\b", " ", q, flags=re.I)
    filters["keywords"] = re.sub(r"\s+", " ", q).strip()
    return filters


def _rank_key(j: dict):
    m = j["match"] or {}
    return (not m.get("eligible", True), -(m.get("score") if m.get("score") is not None else -1))


def search(q: str = "", location: str = "", remote: bool = False, min_salary=None, company: str = "",
           exclude_company: str = "", seniority: str = "", saved_only: bool = False,
           include_ineligible: bool = True, limit: int = 100, user_id=USER_ID) -> dict:
    interpreted = parse_natural_query(q) if q else {"keywords": ""}
    location = location or interpreted.get("location", "")
    remote = remote or interpreted.get("remote", False)
    min_salary = min_salary if min_salary not in (None, "") else interpreted.get("min_salary")
    keywords = interpreted["keywords"].lower().split()
    out = []
    with tx() as c:
        from ..discovery.service import expire
        expire(c)
        for j in rows(c.execute("SELECT * FROM job_postings ORDER BY retrieved_at DESC")):
            j = with_match(c, j, user_id)
            if j.get("discovery") and j["status"] == "expired":
                continue
            m = j["match"] or {}
            hay = " ".join([j["title"], j["company"], j["description"], *j["required_skills"],
                            *j["preferred_skills"]]).lower()
            is_remote = j["work_arrangement"] == "remote" or "remote" in j["location"].lower()
            checks = [
                not keywords or all(k in hay for k in keywords),
                not location or location.lower() in j["location"].lower() or (location.lower() == "remote" and is_remote),
                not remote or is_remote,
                min_salary is None or (j["salary_lpa"] is not None and j["salary_lpa"] >= float(min_salary)),
                not company or company.lower() in j["company"].lower(),
                not exclude_company or exclude_company.lower() not in j["company"].lower(),
                not seniority or m.get("seniority") == seniority,
                not saved_only or j["saved"],
                include_ineligible or m.get("eligible", True),
            ]
            if all(checks):
                out.append(j)
    out.sort(key=_rank_key)
    return {"interpreted": {**interpreted, "location": location, "remote": remote, "min_salary": min_salary},
            "jobs": out[:limit]}


def top_matches(n: int, user_id=USER_ID) -> list:
    return [j for j in search(include_ineligible=False, user_id=user_id)["jobs"]
            if j["status"] == "open" and j["match"] and j["match"]["score"] is not None][:n]


def set_saved(job_id: int, saved: bool, user_id=USER_ID) -> dict:
    get_job(job_id, user_id)
    with tx() as c:
        if saved:
            c.execute("INSERT OR IGNORE INTO saved_jobs(job_id, user_id, saved_at) VALUES (?,?,?)",
                      (job_id, user_id, now()))
        else:
            c.execute("DELETE FROM saved_jobs WHERE job_id=? AND user_id=?", (job_id, user_id))
    return get_job(job_id, user_id)


def check_status(job_id: int, user_id=USER_ID, client: httpx.Client | None = None) -> dict:
    """FR-212. Sites that block automated checks are marked unverified, not expired."""
    job = get_job(job_id, user_id)
    lc = config.app_config()["link_check"]
    own = client is None
    client = client or httpx.Client(timeout=lc["timeout_seconds"], follow_redirects=True,
                                    headers={"User-Agent": lc["user_agent"]})
    try:
        r = client.get(job["source_url"])
        status = "expired" if r.status_code in (404, 410) else "open" if r.status_code < 400 else "unverified"
        detail = f"HTTP {r.status_code}"
    except httpx.HTTPError as e:
        status, detail = "inaccessible", type(e).__name__
    finally:
        if own:
            client.close()
    with tx() as c:
        c.execute("UPDATE job_postings SET status=?, verified_at=? WHERE id=?",
                  (status, now() if status == "open" else job["verified_at"], job_id))
    return {"job_id": job_id, "status": status, "detail": detail}


def delete_job(job_id: int, user_id=USER_ID) -> None:
    with tx() as c:
        if c.execute("SELECT 1 FROM applications WHERE job_id=? AND user_id=? AND status NOT IN ('draft','withdrawn')",
                     (job_id, user_id)).fetchone():
            raise ServiceError("This job has an active application; withdraw it first")
        c.execute("DELETE FROM applications WHERE job_id=? AND user_id=?", (job_id, user_id))
        c.execute("DELETE FROM job_postings WHERE id=?", (job_id,))
