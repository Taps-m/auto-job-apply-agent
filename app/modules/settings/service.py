"""M08 Settings & integrations, including privacy controls (FR-806)."""
import re

from ... import config
from ...core import db, settings_store
from ...core.db import USER_ID, tx
from ...core.errors import ServiceError
from ..agent import gemini
from ..documents import service as documents
from ..profile import service as profile

MODEL_NAME = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
USER_TABLES = ("agent_actions", "chat_sessions", "applications", "saved_jobs", "job_matches", "documents",
               "work_experiences", "career_profiles", "job_preferences")


def current(user_id=USER_ID) -> dict:
    cfg = config.app_config()
    prefs = profile.bundle(user_id)["preferences"]
    return {"version": cfg["version"], "gemini_connected": gemini.connected(), "gemini_model": gemini.model_name(),
            "default_model": cfg["gemini"]["default_model"], "usage": gemini.usage_summary(),
            "search_frequency": prefs["search_frequency"], "automation_level": prefs["automation_level"],
            "search_frequencies": profile.SEARCH_FREQUENCIES, "automation_levels": profile.AUTOMATION_LEVELS,
            "sources": cfg["job_sources"]}


def update(data: dict, user_id=USER_ID) -> dict:
    if "gemini_model" in data:
        name = str(data["gemini_model"]).strip()
        if not MODEL_NAME.match(name):
            raise ServiceError("Invalid model name")
        settings_store.put("gemini_model", name)
    prefs = {k: data[k] for k in ("search_frequency", "automation_level") if k in data}
    if prefs:
        profile.update_preferences(prefs, user_id)
    return current(user_id)


def models() -> list:
    return gemini.list_models()


def delete_all_data(confirm: str, user_id=USER_ID) -> None:
    if confirm != "DELETE":
        raise ServiceError("Type DELETE to confirm")
    documents.delete_files(user_id)
    with tx() as c:
        for table in USER_TABLES:
            c.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM job_postings")
        c.execute("DELETE FROM api_usage")
        c.execute("DELETE FROM integration_settings")
        c.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.init(seed_profile=False)  # Recreate an empty profile with default preferences.
