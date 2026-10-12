"""Gemini API client: model selection, tool-calling loop, usage accounting and error messages (FR-412)."""
from ... import config
from ...core import settings_store
from ...core.db import now, row, rows, tx
from . import tools


def model_name() -> str:
    import os
    return settings_store.get("gemini_model") or os.environ.get("GEMINI_MODEL") or config.app_config()["gemini"]["default_model"]


def connected() -> bool:
    return bool(config.gemini_api_key())


def _client():
    from google import genai
    return genai.Client(api_key=config.gemini_api_key())


def list_models() -> list:
    if not connected():
        return []
    return sorted(m.name.removeprefix("models/") for m in _client().models.list()
                  if "generateContent" in (m.supported_actions or []) and "gemini" in m.name)


def record_usage(model: str, ok: bool, resp=None, error: str = "") -> None:
    um = getattr(resp, "usage_metadata", None)
    with tx() as c:
        c.execute("INSERT INTO api_usage(at, model, ok, input_tokens, output_tokens, error) VALUES (?,?,?,?,?,?)",
                  (now(), model, int(ok), getattr(um, "prompt_token_count", 0) or 0,
                   getattr(um, "candidates_token_count", 0) or 0, error[:300]))


def usage_summary() -> dict:
    with tx() as c:
        total = row(c.execute("SELECT COUNT(*) requests, COALESCE(SUM(ok=0),0) failures,"
                              " COALESCE(SUM(input_tokens),0) input_tokens, COALESCE(SUM(output_tokens),0) output_tokens"
                              " FROM api_usage").fetchone())
        recent = rows(c.execute("SELECT at, model, error FROM api_usage WHERE ok=0 ORDER BY id DESC LIMIT 5"))
    return {**total, "recent_failures": recent,
            "cost_note": "Token counts are from Gemini responses. Check current Gemini pricing for your model to estimate cost."}


def friendly_error(e: Exception) -> str:
    msgs = config.agent_config()["errors"]
    code = str(getattr(e, "code", ""))
    if code in msgs:
        return msgs[code].format(model=model_name())
    return f"Gemini request failed: {type(e).__name__}: {str(e)[:200]}"


def converse(message: str, history: list, system_note: str, session_id, user_id, client=None):
    """Run the tool-calling loop. Returns (reply, tools_used)."""
    from google.genai import types

    acfg, gcfg = config.agent_config(), config.app_config()["gemini"]
    client = client or _client()
    model = model_name()
    cfg = types.GenerateContentConfig(
        system_instruction=acfg["system_prompt"] + "\n\n" + system_note,
        tools=[types.Tool(function_declarations=[
            types.FunctionDeclaration(name=n, description=s["description"], parameters_json_schema=s["parameters"])
            for n, s in tools.schemas().items()])],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role=h["role"], parts=[types.Part(text=h["content"])]) for h in history]
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
    used = []
    for _ in range(gcfg["max_tool_rounds"]):
        try:
            resp = client.models.generate_content(model=model, contents=contents, config=cfg)
        except Exception as e:
            record_usage(model, False, error=str(e))
            raise
        record_usage(model, True, resp)
        calls = resp.function_calls or []
        if not calls:
            return (resp.text or acfg["errors"]["empty"]).strip(), used
        contents.append(resp.candidates[0].content)
        parts = []
        for call in calls:
            result = tools.run(call.name, dict(call.args or {}), session_id, user_id)
            used.append(call.name)
            parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))
        contents.append(types.Content(role="tool", parts=parts))
    return acfg["errors"]["too_many_steps"], used
