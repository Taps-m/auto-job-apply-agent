"""Transparent, deterministic job-match scoring (FR-209).

Gemini may help interpret a vacancy, but the number shown to the user is always
computed here, so every point can be traced to a rule and a weight. Rules and
vocabularies come from config/matching.json; weights and thresholds from the
user's preferences. The score estimates profile compatibility, not a
probability of selection.
"""
import re

from ... import config


def _rules() -> dict:
    return config.matching_rules()


def seniority_labels() -> dict:
    return {int(k): v for k, v in _rules()["seniority_labels"].items()}


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _contains(text: str, phrase: str) -> bool:
    phrase = _norm(phrase)
    if not phrase:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", text) is not None


def seniority_level(title: str):
    t = _norm(title)
    for pattern, level in _rules()["seniority_rules"]:
        if re.search(pattern, t):
            return level
    return None


def required_years(text: str):
    found = [int(m) for m in re.findall(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years|yrs)", _norm(text))]
    return min(found) if found else None


def detect_skills(text: str, vocabulary) -> list:
    t = _norm(text)
    seen, out = set(), []
    for s in vocabulary:
        k = _norm(s)
        if k and k not in seen and _contains(t, k):
            seen.add(k)
            out.append(s)
    return out


def salary_threshold(company: str, prefs: dict) -> float:
    # Exact employer-name match only, so "Google Partner Services" keeps the standard threshold.
    premium = {_norm(c) for c in prefs.get("premium_employers", [])}
    if _norm(company) in premium:
        return prefs.get("premium_min_salary_lpa", prefs.get("min_salary_lpa", 0))
    return prefs.get("min_salary_lpa", 0)


def _city_keys(city: str):
    k = _norm(city)
    return _rules()["city_aliases"].get(k, [k])


def score_job(job: dict, profile: dict, prefs: dict) -> dict:
    title = _norm(job.get("title"))
    body = _norm(" ".join([job.get("description") or "", job.get("responsibilities") or ""]))
    company = job.get("company") or ""
    location = _norm(job.get("location"))
    arrangement = _norm(job.get("work_arrangement"))
    profile_skills = [s for s in profile.get("skills", []) if _norm(s)]
    profile_set = {_norm(s) for s in profile_skills}
    weights = {**config.default_preferences()["weights"], **(prefs.get("weights") or {})}
    rules, labels = _rules(), seniority_labels()
    blockers, components = [], []

    # Exclusion rules (FR-708) make a job ineligible regardless of score.
    for c in prefs.get("excluded_companies", []):
        if _norm(c) and _norm(c) == _norm(company):
            blockers.append(f"Company {company} is excluded in your preferences")
    for loc in prefs.get("excluded_locations", []):
        if _norm(loc) and _contains(location, loc):
            blockers.append(f"Location {loc} is excluded in your preferences")
    for kw in prefs.get("excluded_keywords", []):
        if _norm(kw) and (_contains(title, kw) or _contains(body, kw)):
            blockers.append(f"Contains excluded keyword '{kw}'")

    # Role relevance
    title_hits, body_hits = [], []
    for role in prefs.get("roles", []):
        kws = (prefs.get("role_keywords") or {}).get(role) or [role]
        if any(_contains(title, k) for k in kws):
            title_hits.append(role)
        elif any(_contains(body, k) for k in kws):
            body_hits.append(role)
    if title_hits:
        components.append(("role", 1.0, f"Title matches target role: {', '.join(title_hits)}"))
    elif body_hits:
        components.append(("role", rules["role_in_description_score"], f"Description mentions target role area: {', '.join(body_hits)}; title does not"))
    else:
        components.append(("role", 0.0, "No target role area found in the title or description"))

    # Skills
    required = [s for s in job.get("required_skills", []) if _norm(s)]
    preferred = [s for s in job.get("preferred_skills", []) if _norm(s)]
    skills_source = "listed on the vacancy"
    if not required and not preferred:
        required = detect_skills(f"{title} {body}", profile_skills + rules["builtin_skills"])
        skills_source = "detected in the description (estimate)"
    missing_required = [s for s in required if _norm(s) not in profile_set]
    missing_preferred = [s for s in preferred if _norm(s) not in profile_set]
    if not required and not preferred:
        components.append(("skills", None, "No skills listed or detected"))
    elif not profile_set:
        components.append(("skills", None, "Add skills to your profile to score this"))
    else:
        total = 2 * len(required) + len(preferred)
        got = 2 * (len(required) - len(missing_required)) + (len(preferred) - len(missing_preferred))
        components.append(("skills", got / total,
                           f"{len(required) - len(missing_required)}/{len(required)} required and "
                           f"{len(preferred) - len(missing_preferred)}/{len(preferred)} preferred skills, {skills_source}"))

    # Experience and seniority
    level = seniority_level(job.get("title"))
    years_needed = required_years(body)
    years_have = profile.get("years_experience")
    parts, notes = [], []
    lo, hi = prefs.get("seniority_min", 0), prefs.get("seniority_max", 6)
    if level is not None:
        gap = lo - level if level < lo else level - hi if level > hi else 0
        parts.append(1.0 if gap == 0 else 0.5 if gap == 1 else 0.0)
        notes.append(f"{labels[level]} title vs target {labels[lo]}–{labels[hi]}")
    if years_needed is not None and years_have is not None:
        short = years_needed - years_have
        parts.append(1.0 if short <= 0 else 0.5 if short <= 2 else 0.0)
        notes.append(f"asks {years_needed}+ years, you have {years_have:g}")
    elif years_needed is not None:
        notes.append(f"asks {years_needed}+ years; add your experience to compare")
    components.append(("experience", sum(parts) / len(parts) if parts else None,
                       "; ".join(notes) if notes else "Seniority and required experience unknown"))

    # Location and work arrangement
    allowed = [_norm(a) for a in prefs.get("arrangements", [])]
    is_remote = "remote" in arrangement or _contains(location, "remote")
    if arrangement and not any(a in arrangement for a in allowed) and not (is_remote and "remote" in allowed):
        components.append(("location", 0.0, f"{job.get('work_arrangement')} is not an accepted arrangement"))
    elif is_remote and "remote" in allowed:
        components.append(("location", 1.0, "Remote role, and you accept remote work"))
    elif location:
        rank = next((i for i, c in enumerate(prefs.get("cities", []))
                     if any(_contains(location, k) for k in _city_keys(c))), None)
        if rank is None:
            components.append(("location", 0.0, f"{job.get('location')} is not one of your preferred cities"))
        else:
            components.append(("location", max(rules["location_rank_floor"], 1 - rules["location_rank_step"] * rank),
                               f"{prefs['cities'][rank]} is preference #{rank + 1}"))
    else:
        components.append(("location", None, "Location not stated"))

    # Compensation
    salary = job.get("salary_lpa")
    threshold = salary_threshold(company, prefs)
    if salary is None:
        if not prefs.get("allow_unknown_salary", True):
            blockers.append("Salary not disclosed, and your preferences require a disclosed salary")
        components.append(("compensation", None, "Salary not disclosed"))
    elif salary >= threshold:
        components.append(("compensation", 1.0, f"₹{salary:g} LPA meets your ₹{threshold:g} LPA minimum"))
    else:
        blockers.append(f"₹{salary:g} LPA is below your ₹{threshold:g} LPA minimum")
        components.append(("compensation", 0.0, f"₹{salary:g} LPA is below your ₹{threshold:g} LPA minimum"))

    known = [(n, s) for n, s, _ in components if s is not None]
    known_weight = sum(weights.get(n, 0) for n, _ in known)
    total_weight = sum(weights.get(n, 0) for n, _, _ in components) or 1
    score = round(sum(weights.get(n, 0) * s for n, s in known) / known_weight * 100) if known_weight else None
    return {
        "score": score,
        "eligible": not blockers,
        "blockers": blockers,
        "coverage": round(known_weight / total_weight * 100),
        "components": [{"name": n, "weight": weights.get(n, 0),
                        "score": None if s is None else round(s * 100), "reason": r} for n, s, r in components],
        # Without profile skills every skill would look missing, so report no gap analysis instead.
        "skills_gap": {"required": missing_required, "preferred": missing_preferred} if profile_set else None,
        "seniority": None if level is None else labels[level],
        "note": "Estimated profile compatibility, not a probability of selection. "
                "Unknown factors are left out of the score; coverage shows how much of the score is based on known data.",
    }
