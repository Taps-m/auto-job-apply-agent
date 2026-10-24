import os
import shutil
import tempfile

# Isolate tests from real data and from any real Gemini key before the app is imported.
os.environ["PJA_DATA_DIR"] = tempfile.mkdtemp(prefix="pja-test-")
os.environ["GEMINI_API_KEY"] = ""
os.environ["PJA_DISABLE_DISCOVERY"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    db.db_path().unlink(missing_ok=True)
    shutil.rmtree(db.data_dir() / "documents", ignore_errors=True)
    db.init()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def profile(client):
    client.put("/api/profile", json={
        "preferred_name": "Tapo", "headline": "Credit risk analyst", "years_experience": 5,
        "skills": "Python, SQL, Credit risk, IFRS 9, Machine learning", "notice_months": 2})


def job_payload(**over):
    base = {"title": "Credit Risk Manager", "company": "HSBC", "source_url": "https://example.com/jobs/1",
            "location": "Pune", "work_arrangement": "hybrid", "salary_lpa": 30,
            "description": "Build IFRS 9 models in Python and SQL. 4+ years experience.",
            "required_skills": "Python, SQL, SAS", "preferred_skills": "Tableau"}
    base.update(over)
    return base
