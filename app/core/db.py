"""SQLite storage. Table names follow the FRS database design so a later move to PostgreSQL is a driver swap."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .. import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  preferred_name TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS career_profiles (
  user_id INTEGER PRIMARY KEY REFERENCES users(id),
  headline TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL DEFAULT '',
  years_experience REAL,
  skills TEXT NOT NULL DEFAULT '[]',
  career_goals TEXT NOT NULL DEFAULT '',
  github_url TEXT NOT NULL DEFAULT '',
  website_url TEXT NOT NULL DEFAULT '',
  notice_months INTEGER,
  work_authorization TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS work_experiences (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  employer TEXT NOT NULL,
  role TEXT NOT NULL,
  start_date TEXT NOT NULL DEFAULT '',
  end_date TEXT NOT NULL DEFAULT '',
  achievements TEXT NOT NULL DEFAULT '',
  verified INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS job_preferences (
  user_id INTEGER PRIMARY KEY REFERENCES users(id),
  data TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_postings (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  company TEXT NOT NULL,
  location TEXT NOT NULL DEFAULT '',
  work_arrangement TEXT NOT NULL DEFAULT '',
  employment_type TEXT NOT NULL DEFAULT '',
  salary_lpa REAL,
  description TEXT NOT NULL DEFAULT '',
  responsibilities TEXT NOT NULL DEFAULT '',
  required_skills TEXT NOT NULL DEFAULT '[]',
  preferred_skills TEXT NOT NULL DEFAULT '[]',
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  dedupe_key TEXT NOT NULL UNIQUE,
  posted_at TEXT,
  retrieved_at TEXT NOT NULL,
  verified_at TEXT,
  status TEXT NOT NULL DEFAULT 'open'
);
CREATE TABLE IF NOT EXISTS job_matches (
  job_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id),
  score REAL,
  breakdown TEXT NOT NULL,
  calculated_at TEXT NOT NULL,
  PRIMARY KEY (job_id, user_id)
);
CREATE TABLE IF NOT EXISTS saved_jobs (
  job_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id),
  saved_at TEXT NOT NULL,
  PRIMARY KEY (job_id, user_id)
);
CREATE TABLE IF NOT EXISTS applications (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  job_id INTEGER NOT NULL REFERENCES job_postings(id),
  status TEXT NOT NULL,
  resume_document_id INTEGER REFERENCES documents(id),
  cover_letter TEXT NOT NULL DEFAULT '',
  answers TEXT NOT NULL DEFAULT '{}',
  approved_at TEXT,
  opened_external_at TEXT,
  submitted_at TEXT,
  confirmation TEXT NOT NULL DEFAULT '',
  follow_up_on TEXT,
  follow_up_note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS application_events (
  id INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  at TEXT NOT NULL,
  kind TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  kind TEXT NOT NULL,
  filename TEXT NOT NULL,
  stored_path TEXT NOT NULL,
  is_master INTEGER NOT NULL DEFAULT 0,
  job_id INTEGER REFERENCES job_postings(id),
  uploaded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_sessions (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  title TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_messages (
  id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  context TEXT NOT NULL DEFAULT '{}',
  at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_actions (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  session_id INTEGER REFERENCES chat_sessions(id),
  tool TEXT NOT NULL,
  arguments TEXT NOT NULL,
  status TEXT NOT NULL,
  result TEXT NOT NULL DEFAULT '',
  proposed_at TEXT NOT NULL,
  decided_at TEXT
);
CREATE TABLE IF NOT EXISTS integration_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS api_usage (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  model TEXT NOT NULL,
  ok INTEGER NOT NULL,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  error TEXT NOT NULL DEFAULT ''
);
"""

USER_ID = 1  # Single local user; every query is still scoped by user_id.


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def data_dir() -> Path:
    return config.app_config()["data_dir"]


def db_path() -> Path:
    return data_dir() / "assistant.db"


def connect() -> sqlite3.Connection:
    data_dir().mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def tx():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row(r):
    return dict(r) if r is not None else None


def rows(rs):
    return [dict(r) for r in rs]


def init(seed_profile: bool = True) -> None:
    """Create tables and, on first run, the local user with default preferences from config."""
    legacy_state = data_dir() / "state.json"
    with tx() as c:
        c.executescript(SCHEMA)
        if c.execute("SELECT 1 FROM users WHERE id=?", (USER_ID,)).fetchone():
            return
        t = now()
        c.execute("INSERT INTO users(id, preferred_name, created_at) VALUES (?, '', ?)", (USER_ID, t))
        prefs = dict(config.default_preferences())
        notice = None
        auth = ""
        # One-time import of preferences saved by releases before V 0.3.0 (data/state.json).
        if legacy_state.exists():
            try:
                old = json.loads(legacy_state.read_text(encoding="utf-8")).get("preferences", {})
                if isinstance(old.get("minimumCTCLPA"), (int, float)):
                    prefs["min_salary_lpa"] = old["minimumCTCLPA"]
                if isinstance(old.get("allowUnknownSalary"), bool):
                    prefs["allow_unknown_salary"] = old["allowUnknownSalary"]
                notice = old.get("noticeMonths")
                auth = old.get("workAuthorization", "")
            except (ValueError, OSError):
                pass
        c.execute("INSERT INTO job_preferences(user_id, data, updated_at) VALUES (?,?,?)",
                  (USER_ID, json.dumps(prefs), t))
        seed = config.app_config()["profile_seed"] if seed_profile else {}
        c.execute(
            "INSERT INTO career_profiles(user_id, github_url, website_url, notice_months, work_authorization, updated_at)"
            " VALUES (?,?,?,?,?,?)",
            (USER_ID, seed.get("github_url", ""), seed.get("website_url", ""), notice, auth, t))
