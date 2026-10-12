"""Conversations (FR-401, FR-402, FR-410) and context-aware suggestions (FR-409)."""
import json

from ... import config
from ...core.db import USER_ID, now, rows, tx
from ...core.errors import ServiceError
from ..applications import service as applications
from ..jobs import service as jobs
from ..profile.service import get_preferences
from . import gemini, tools


def sessions(user_id=USER_ID) -> list:
    with tx() as c:
        return rows(c.execute("SELECT * FROM chat_sessions WHERE user_id=? ORDER BY id DESC LIMIT 50", (user_id,)))


def messages(session_id: int, user_id=USER_ID) -> list:
    with tx() as c:
        if not c.execute("SELECT 1 FROM chat_sessions WHERE id=? AND user_id=?", (session_id, user_id)).fetchone():
            raise ServiceError("Conversation not found", 404)
        return rows(c.execute("SELECT id, role, content, at FROM chat_messages WHERE session_id=? ORDER BY id", (session_id,)))


def suggestions(screen: str, job_id: int | None = None, user_id=USER_ID) -> list:
    templates = config.agent_config()["suggestions"]
    with tx() as c:
        city = (get_preferences(c, user_id).get("cities") or ["my preferred city"])[0]
    if screen == "job" and job_id:
        j = jobs.get_job(job_id, user_id)
        return [t.format(job=f"{j['title']} at {j['company']}") for t in templates["job"]]
    return [t.format(city=city) for t in templates.get(screen, templates["default"])]


def context_note(context: dict, user_id) -> str:
    """Resolve only the selected job/application, not the user's full records (FR-402)."""
    parts = [f"Today is {now()[:10]}. The user is on the '{context.get('screen', 'home')}' screen."]
    try:
        if context.get("job_id"):
            j = jobs.get_job(int(context["job_id"]), user_id)
            parts.append("Selected job (call get_job_details for more): " + json.dumps(tools.job_summary(j)))
        if context.get("application_id"):
            a = applications.get(int(context["application_id"]), user_id)
            parts.append("Selected application: " + json.dumps(tools.application_summary(a)))
    except (ServiceError, ValueError):
        pass
    return "\n".join(parts)


def _store(c, session_id, role, content, ctx) -> None:
    c.execute("INSERT INTO chat_messages(session_id, role, content, context, at) VALUES (?,?,?,?,?)",
              (session_id, role, content, json.dumps(ctx), now()))


def send(message: str, session_id: int | None, context: dict, user_id=USER_ID, client=None) -> dict:
    message = str(message or "").strip()[:4000]
    if not message:
        raise ServiceError("Type a message")
    limit = config.app_config()["gemini"]["history_messages"]
    with tx() as c:
        if session_id is None:
            session_id = c.execute("INSERT INTO chat_sessions(user_id, title, created_at) VALUES (?,?,?)",
                                   (user_id, message[:60], now())).lastrowid
        elif not c.execute("SELECT 1 FROM chat_sessions WHERE id=? AND user_id=?", (session_id, user_id)).fetchone():
            raise ServiceError("Conversation not found", 404)
        history = rows(c.execute("SELECT role, content FROM (SELECT * FROM chat_messages WHERE session_id=?"
                                 " AND role IN ('user','model') ORDER BY id DESC LIMIT ?) ORDER BY id", (session_id, limit)))
        _store(c, session_id, "user", message, context)

    used = []
    try:
        if client is None and not gemini.connected():
            raise ServiceError(config.agent_config()["errors"]["not_connected"], 503)
        reply, used = gemini.converse(message, history, context_note(context, user_id), session_id, user_id, client)
        role = "model"
    except ServiceError as e:
        reply, role = str(e), "error"
    except Exception as e:  # Gemini/network failures are reported, never fatal.
        reply, role = gemini.friendly_error(e), "error"
    with tx() as c:
        _store(c, session_id, role, reply, {"tools": used})
    return {"session_id": session_id, "role": role, "reply": reply, "tools_used": used,
            "pending_actions": tools.pending(user_id)}
