"""Background discovery with persisted outcomes, deduplication and daily scheduling."""
import json
import logging
import os
import threading
from datetime import datetime, timedelta, timezone

import httpx

from ... import config
from ...core.db import USER_ID, now, row, tx
from ...core.errors import ServiceError
from ..jobs import service as jobs
from ..profile.service import get_preferences
from . import himalayas

log = logging.getLogger(__name__)
_lock = threading.Lock()
_stop = threading.Event()
_scheduler = None
_worker = None


def ensure(c):
    c.execute("CREATE TABLE IF NOT EXISTS discovery_runs (id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL, detail TEXT NOT NULL, counts TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS discovered_jobs (guid TEXT PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE, expires_at TEXT NOT NULL, salary_text TEXT NOT NULL)")


def expire(c):
    ensure(c)
    c.execute("UPDATE job_postings SET status='expired' WHERE id IN (SELECT job_id FROM discovered_jobs WHERE expires_at<=?)", (now(),))


def status():
    with tx() as c:
        expire(c)
        last = row(c.execute("SELECT * FROM discovery_runs ORDER BY id DESC LIMIT 1").fetchone())
        frequency = get_preferences(c).get("search_frequency", "daily")
    if last:
        last["counts"] = json.loads(last["counts"])
    return {"source": "Himalayas", "source_url": "https://himalayas.app", "frequency": frequency,
            "running": _lock.locked(), "last_run": last, "automatic_submission": False,
            "schedule_note": "Scheduled searches run while this app is open. Other portals are not connected."}


def save_progress(run_id, counts, detail, state="running"):
    with tx() as c:
        c.execute("UPDATE discovery_runs SET counts=?,detail=?,status=?,finished_at=? WHERE id=?",
                  (json.dumps(counts), detail, state, None if state == "running" else now(), run_id))


def queries():
    cfg = json.loads((config.CONFIG_DIR / "discovery.json").read_text(encoding="utf-8"))
    with tx() as c:
        prefs = get_preferences(c)
    categories = list(prefs.get("roles", []))
    if "Global Capability Centres" in prefs.get("industries", []):
        categories.append("Global Capability Centres")
    terms = list(dict.fromkeys(q for role in categories for q in cfg["queries"].get(role, [role]) if q.strip()))
    return cfg, terms


def run(run_id, client=None, wait=None):
    counts = {"fetched": 0, "added": 0, "duplicates": 0, "skipped": 0, "pages": 0}
    own = client is None
    client = client or httpx.Client(timeout=25, follow_redirects=False, headers={"User-Agent": "CareerAI/0.6 personal job discovery"})
    wait = wait or _stop.wait
    seen, finished = set(), set()
    try:
        cfg, terms = queries()
        for page in range(1, cfg["pages_per_query"] + 1):
            for term in terms:
                if term in finished:
                    continue
                if wait(cfg["request_interval_seconds"]):
                    save_progress(run_id, counts, "Search interrupted; saved jobs are retained.", "interrupted")
                    return
                batch = himalayas.fetch_page(client, term, page)
                counts["pages"] += 1
                if not batch:
                    finished.add(term)
                for raw in batch:
                    counts["fetched"] += 1
                    if not isinstance(raw, dict):
                        counts["skipped"] += 1
                        continue
                    guid = raw.get("guid")
                    if not isinstance(guid, str) or guid in seen:
                        counts["duplicates"] += 1
                        continue
                    seen.add(guid)
                    normalized = himalayas.normalize(raw)
                    if not normalized:
                        counts["skipped"] += 1
                        continue
                    payload, meta = normalized
                    with tx() as c:
                        existing = c.execute("SELECT job_id FROM discovered_jobs WHERE guid=?", (guid,)).fetchone()
                    if existing:
                        counts["duplicates"] += 1
                        with tx() as c:
                            c.execute("UPDATE discovered_jobs SET expires_at=?,salary_text=? WHERE guid=?", (meta["expires_at"], meta["salary_text"], guid))
                            c.execute("UPDATE job_postings SET description=?,source_url=?,employment_type=?,posted_at=?,retrieved_at=?,status='open' WHERE id=? AND source_name='Himalayas'",
                                      (payload["description"], payload["source_url"], payload["employment_type"], payload["posted_at"], now(), existing["job_id"]))
                        from ..matching import service as matching
                        matching.recompute(USER_ID, [existing["job_id"]])
                        continue
                    try:
                        result = jobs.add_job(payload)
                        job_id = result["job"]["id"]
                        counts["duplicates" if result["merged_with_existing"] else "added"] += 1
                    except ServiceError as exc:
                        if exc.status == 409 and exc.data.get("job_id"):
                            job_id = exc.data["job_id"]
                            counts["duplicates"] += 1
                        else:
                            counts["skipped"] += 1
                            continue
                    with tx() as c:
                        c.execute("INSERT OR REPLACE INTO discovered_jobs(guid,job_id,expires_at,salary_text) VALUES(?,?,?,?)",
                                  (guid, job_id, meta["expires_at"], meta["salary_text"]))
                save_progress(run_id, counts, f"Searching {term}, page {page}.")
        detail = "Search finished."
        if len(finished) < len(terms):
            detail += f" Recent-results window: up to {cfg['pages_per_query']} pages per search term; more jobs may exist."
        save_progress(run_id, counts, detail, "completed")
    except httpx.HTTPStatusError as exc:
        message = "Source rate limit reached; retry later." if exc.response.status_code == 429 else f"Source returned HTTP {exc.response.status_code}; retry later."
        save_progress(run_id, counts, message + " Any jobs already found are saved.", "failed")
    except (httpx.HTTPError, ValueError):
        save_progress(run_id, counts, "Source unavailable or returned an unexpected response. Any jobs already found are saved.", "failed")
    except Exception:
        log.exception("Discovery failed")
        save_progress(run_id, counts, "Search stopped unexpectedly. Any jobs already found are saved.", "failed")
    finally:
        if own:
            client.close()


def start():
    global _worker
    if not _lock.acquire(blocking=False):
        raise ServiceError("A job search is already running", 409)
    try:
        with tx() as c:
            ensure(c)
            cur = c.execute("INSERT INTO discovery_runs(started_at,status,detail,counts) VALUES(?,'running','Starting search','{}')", (now(),))
            run_id = cur.lastrowid
        def work():
            try:
                run(run_id)
            finally:
                _lock.release()
        _worker = threading.Thread(target=work, name="job-discovery", daemon=True)
        _worker.start()
        return {"run_id": run_id, "status": "running"}
    except Exception:
        _lock.release()
        raise


def due():
    s = status()
    if s["running"] or s["frequency"] not in ("daily", "weekly"):
        return False
    last = s["last_run"]
    days = 7 if s["frequency"] == "weekly" else 1
    return not last or datetime.fromisoformat(last["started_at"]) + timedelta(days=days) <= datetime.now(timezone.utc)


def startup():
    global _scheduler
    if os.environ.get("PJA_DISABLE_DISCOVERY") == "1":
        return
    _stop.clear()
    with tx() as c:
        ensure(c)
        c.execute("UPDATE discovery_runs SET status='interrupted',finished_at=?,detail='Previous search was interrupted. Retry with Search now.' WHERE status='running'", (now(),))
    def schedule():
        while not _stop.wait(30):
            try:
                if due():
                    start()
            except Exception:
                log.exception("Discovery schedule check failed")
    _scheduler = threading.Thread(target=schedule, name="discovery-scheduler", daemon=True)
    _scheduler.start()


def shutdown():
    _stop.set()
    if _worker:
        _worker.join(timeout=30)
    if _scheduler:
        _scheduler.join(timeout=2)
