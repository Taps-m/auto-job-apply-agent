from fastapi import APIRouter, Body

from . import chat, tools

router = APIRouter(prefix="/api", tags=["agent"])


@router.post("/chat")
def send(data: dict = Body(...)):
    sid = data.get("session_id")
    return chat.send(data.get("message", ""), int(sid) if sid else None, data.get("context") or {})


@router.get("/chat/sessions")
def sessions():
    return chat.sessions()


@router.get("/chat/sessions/{session_id}")
def session_messages(session_id: int):
    return chat.messages(session_id)


@router.get("/chat/suggestions")
def suggestions(screen: str = "home", job_id: int | None = None):
    return chat.suggestions(screen, job_id)


@router.get("/actions")
def actions():
    return tools.pending()


@router.post("/actions/{action_id}")
def decide(action_id: int, data: dict = Body(...)):
    return tools.decide(action_id, bool(data.get("approve")))
