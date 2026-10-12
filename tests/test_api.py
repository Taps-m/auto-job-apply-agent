from conftest import job_payload


def test_rejects_foreign_host_and_cross_site_post(client):
    assert client.get("/api/home", headers={"host": "evil.example"}).status_code == 403
    r = client.post("/api/jobs", json=job_payload(), headers={"origin": "http://evil.example"})
    assert r.status_code == 403


def test_job_requires_source_link(client):
    r = client.post("/api/jobs", json=job_payload(source_url="ftp://x"))
    assert r.status_code == 400 and "source link" in r.json()["error"]


def test_duplicate_link_and_cross_source_merge(client):
    first = client.post("/api/jobs", json=job_payload(salary_lpa=None)).json()["job"]
    again = client.post("/api/jobs", json=job_payload())
    assert again.status_code == 409 and again.json()["job_id"] == first["id"]
    merged = client.post("/api/jobs", json=job_payload(source_url="https://other.example/7", company="HSBC India Pvt Ltd")).json()
    assert merged["merged_with_existing"] and merged["job"]["id"] == first["id"]
    assert merged["job"]["salary_lpa"] == 30  # gap filled from second source
    assert len(client.get("/api/jobs").json()["jobs"]) == 1


def test_home_top_matches_skip_ineligible(client, profile):
    client.post("/api/jobs", json=job_payload())
    client.post("/api/jobs", json=job_payload(source_url="https://example.com/2", company="LowPay", salary_lpa=10))
    home = client.get("/api/home").json()
    assert home["preferred_name"] == "Tapo"
    assert [j["company"] for j in home["top_matches"]] == ["HSBC"]
    assert len(client.get("/api/jobs?include_ineligible=false").json()["jobs"]) == 1


def test_search_filters(client):
    client.post("/api/jobs", json=job_payload())
    client.post("/api/jobs", json=job_payload(source_url="https://example.com/2", title="Data Scientist",
                                              company="Fintech Co", location="Kolkata", salary_lpa=40))
    jobs = client.get("/api/jobs", params={"q": "data scientist jobs in Kolkata above 35 LPA"}).json()["jobs"]
    assert [j["company"] for j in jobs] == ["Fintech Co"]
    assert client.get("/api/jobs", params={"exclude_company": "fintech"}).json()["jobs"][0]["company"] == "HSBC"


def test_application_workflow_requires_approval_and_confirmation(client, profile):
    job = client.post("/api/jobs", json=job_payload()).json()["job"]
    app = client.post("/api/applications", json={"job_id": job["id"]}).json()
    assert app["status"] == "draft" and not app["readiness"]["ready"]  # no resume yet
    assert client.post(f"/api/applications/{app['id']}/approve").status_code == 422
    assert client.post(f"/api/applications/{app['id']}/open").status_code == 400

    doc = client.post("/api/documents", files={"file": ("cv.pdf", b"%PDF-1.4 test", "application/pdf")}).json()
    client.put(f"/api/applications/{app['id']}", json={"resume_document_id": doc["id"], "cover_letter": "Hello"})
    assert client.post(f"/api/applications/{app['id']}/approve").json()["status"] == "approved"

    opened = client.post(f"/api/applications/{app['id']}/open").json()
    assert opened["url"] == job["source_url"]
    assert opened["application"]["status"] == "awaiting_confirmation"  # opening is not submitting
    assert opened["application"]["submitted_at"] is None
    assert client.post(f"/api/applications/{app['id']}/confirm", json={"confirmation": ""}).status_code == 400
    done = client.post(f"/api/applications/{app['id']}/confirm", json={"confirmation": "REF-123"}).json()
    assert done["status"] == "submitted"
    assert client.post(f"/api/applications/{app['id']}/outcome", json={"status": "interview"}).json()["status"] == "interview"
    kinds = [e["kind"] for e in done["events"]]
    assert kinds == ["created", "edited", "approved", "opened_employer_page", "submitted"]
    assert client.get("/api/applications").json()["metrics"]["interviews"] == 1


def test_outcome_needs_submission_and_duplicates_warn(client, profile):
    job = client.post("/api/jobs", json=job_payload()).json()["job"]
    app = client.post("/api/applications", json={"job_id": job["id"]}).json()
    assert client.post(f"/api/applications/{app['id']}/outcome", json={"status": "offer"}).status_code == 400
    dup = client.post("/api/applications", json={"job_id": job["id"]})
    assert dup.status_code == 409 and dup.json()["application_id"] == app["id"]


def test_upload_validates_content(client):
    r = client.post("/api/documents", files={"file": ("cv.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 400
    r = client.post("/api/documents", files={"file": ("cv.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 400


def test_preferences_validation_and_rescore(client, profile):
    job = client.post("/api/jobs", json=job_payload(salary_lpa=22)).json()["job"]
    assert not job["match"]["eligible"]
    client.put("/api/preferences", json={"min_salary_lpa": 20})
    assert client.get(f"/api/jobs/{job['id']}").json()["match"]["eligible"]
    assert client.put("/api/preferences", json={"seniority_min": 5, "seniority_max": 2}).status_code == 400
    assert client.put("/api/preferences", json={"arrangements": ["moon"]}).status_code == 400


def test_delete_all_data(client, profile):
    client.post("/api/jobs", json=job_payload())
    assert client.post("/api/privacy/delete-all", json={"confirm": "no"}).status_code == 400
    assert client.post("/api/privacy/delete-all", json={"confirm": "DELETE"}).json()["ok"]
    assert client.get("/api/jobs").json()["jobs"] == []
    assert client.get("/api/profile").json()["profile"]["preferred_name"] == ""
