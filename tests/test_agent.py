from types import SimpleNamespace

from google.genai import types

from app.modules.agent import chat, tools
from conftest import job_payload


def test_tool_arguments_are_validated(client):
    assert "Unexpected" in tools.run("get_job_details", {"job_id": 1, "user_id": 2})["error"]
    assert "Missing" in tools.run("get_job_details", {})["error"]
    assert "must be integer" in tools.run("get_job_details", {"job_id": "abc"})["error"]
    assert "Unknown tool" in tools.run("submit_approved_application", {"application_id": 1})["error"]
    assert "not found" in tools.run("get_job_details", {"job_id": 999})["error"]


def test_agent_has_no_submission_tool():
    assert not any("submit" in name for name in tools.schemas())
    assert set(tools.schemas()) == set(tools.HANDLERS)


def test_profile_sent_to_agent_excludes_documents(client, profile):
    client.post("/api/documents", files={"file": ("cv.pdf", b"%PDF-1.4", "application/pdf")})
    p = tools.run("get_user_profile", {})
    assert p["preferred_name"] == "Tapo" and "documents" not in p and "work_authorization" not in p


def test_proposals_wait_for_user_approval(client):
    job = client.post("/api/jobs", json=job_payload()).json()["job"]
    res = tools.run("propose_application_draft", {"job_id": job["id"], "reason": "good fit"})
    assert client.get("/api/applications").json()["applications"] == []  # nothing changed yet
    decided = client.post(f"/api/actions/{res['pending_action_id']}", json={"approve": True}).json()
    assert decided["status"] == "executed"
    assert client.get("/api/applications").json()["applications"][0]["status"] == "draft"
    assert client.post(f"/api/actions/{res['pending_action_id']}", json={"approve": True}).status_code == 400


def test_chat_without_key_reports_not_connected(client):
    r = client.post("/api/chat", json={"message": "hi", "context": {"screen": "home"}}).json()
    assert r["role"] == "error" and "not connected" in r["reply"]
    assert client.get(f"/api/chat/sessions/{r['session_id']}").json()[0]["content"] == "hi"


class FakeModels:
    """Replays a function call, then a text answer, recording what Gemini was sent."""

    def __init__(self, job_id):
        self.job_id, self.calls = job_id, []

    def generate_content(self, model, contents, config):
        self.calls.append(contents)
        usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=5)
        if len(self.calls) == 1:
            fc = types.FunctionCall(name="calculate_job_match", args={"job_id": self.job_id})
            return SimpleNamespace(function_calls=[fc], usage_metadata=usage, text=None,
                                   candidates=[SimpleNamespace(content=types.Content(role="model", parts=[types.Part(function_call=fc)]))])
        return SimpleNamespace(function_calls=None, usage_metadata=usage, text="Recommendation: apply.", candidates=[])


def test_chat_runs_tools_and_records_usage(client, profile):
    job = client.post("/api/jobs", json=job_payload()).json()["job"]
    fake = FakeModels(job["id"])
    r = chat.send("How well do I fit?", None, {"screen": "job", "job_id": job["id"]}, client=SimpleNamespace(models=fake))
    assert r["reply"] == "Recommendation: apply." and r["tools_used"] == ["calculate_job_match"]
    tool_turn = fake.calls[1][-1]
    assert tool_turn.parts[0].function_response.response["result"]["score"] == job["match"]["score"]
    usage = client.get("/api/settings").json()["usage"]
    assert usage["requests"] == 2 and usage["input_tokens"] == 20


def test_suggestions_follow_screen(client):
    job = client.post("/api/jobs", json=job_payload()).json()["job"]
    assert "missing" in client.get(f"/api/chat/suggestions?screen=job&job_id={job['id']}").json()[0]
    assert "follow-up" in client.get("/api/chat/suggestions?screen=applications").json()[0]
