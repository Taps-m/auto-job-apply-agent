from app import config
from app.modules.jobs.service import parse_natural_query
from app.modules.matching import scoring

P = config.default_preferences()
PROFILE = {"skills": ["Python", "SQL", "Credit risk"], "years_experience": 5}


def job(**over):
    base = {"title": "Credit Risk Manager", "company": "HSBC", "location": "Pune", "work_arrangement": "hybrid",
            "salary_lpa": 30, "description": "", "responsibilities": "", "required_skills": ["Python", "SAS"],
            "preferred_skills": []}
    base.update(over)
    return base


def comp(result, name):
    return next(c for c in result["components"] if c["name"] == name)


def test_premium_threshold_requires_exact_employer_name():
    assert scoring.salary_threshold(" google ", P) == 20
    assert scoring.salary_threshold("Google Partner Services", P) == 25
    assert scoring.score_job(job(company="Google", salary_lpa=20), PROFILE, P)["eligible"]
    assert not scoring.score_job(job(company="Google", salary_lpa=19.9), PROFILE, P)["eligible"]
    assert not scoring.score_job(job(company="Google Partner Services", salary_lpa=20), PROFILE, P)["eligible"]


def test_unknown_salary_is_left_out_of_score_not_penalised():
    r = scoring.score_job(job(salary_lpa=None), PROFILE, P)
    assert r["eligible"] and comp(r, "compensation")["score"] is None and r["coverage"] == 85
    assert not scoring.score_job(job(salary_lpa=None), PROFILE, {**P, "allow_unknown_salary": False})["eligible"]


def test_seniority_specific_titles_win():
    assert scoring.seniority_level("AVP - Market Risk") == 4
    assert scoring.seniority_level("Assistant Vice President, Credit") == 4
    assert scoring.seniority_level("Vice President, Credit") == 5
    assert scoring.seniority_level("Senior Analyst") == 2
    assert scoring.seniority_level("Analyst") == 1
    assert scoring.seniority_level("Credit Risk") is None


def test_skills_weight_required_twice_and_report_gaps():
    r = scoring.score_job(job(required_skills=["Python", "SAS"], preferred_skills=["SQL"]), PROFILE, P)
    assert comp(r, "skills")["score"] == 60  # (2 + 0 + 1) / 5
    assert r["skills_gap"] == {"required": ["SAS"], "preferred": []}


def test_skills_detected_from_description_when_not_listed():
    r = scoring.score_job(job(required_skills=[], description="Strong python and tableau needed"), PROFILE, P)
    assert "estimate" in comp(r, "skills")["reason"] and r["skills_gap"]["required"] == ["tableau"]


def test_location_aliases_remote_and_disallowed_arrangement():
    assert comp(scoring.score_job(job(location="Bangalore"), PROFILE, P), "location")["score"] == 100
    assert comp(scoring.score_job(job(location="Gurgaon"), PROFILE, P), "location")["score"] > 60
    assert comp(scoring.score_job(job(location="London", work_arrangement="remote"), PROFILE, P), "location")["score"] == 100
    no_remote = {**P, "arrangements": ["hybrid"]}
    assert comp(scoring.score_job(job(work_arrangement="remote"), PROFILE, no_remote), "location")["score"] == 0


def test_exclusions_block_job():
    prefs = {**P, "excluded_companies": ["hsbc"], "excluded_keywords": ["sales"]}
    r = scoring.score_job(job(description="Some sales targets"), PROFILE, prefs)
    assert not r["eligible"] and len(r["blockers"]) == 2


def test_experience_years_compared():
    r = scoring.score_job(job(title="Credit risk", description="Requires 8+ years"), PROFILE, P)
    assert comp(r, "experience")["score"] == 0
    r = scoring.score_job(job(title="Credit risk", description="Requires 3-5 years"), PROFILE, P)
    assert comp(r, "experience")["score"] == 100


def test_natural_language_query():
    f = parse_natural_query("credit risk jobs in Kolkata above 30 LPA")
    assert f == {"min_salary": 30.0, "location": "Kolkata", "keywords": "credit risk"}
    assert parse_natural_query("remote fintech roles")["remote"] is True
