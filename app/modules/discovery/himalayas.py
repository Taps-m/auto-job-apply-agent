"""Official public API: https://himalayas.app/api. No credentials needed."""
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse

API = "https://himalayas.app/jobs/api"


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain(value):
    parser = PlainText()
    parser.feed(str(value or ""))
    return " ".join(" ".join(parser.parts).split())


def timestamp(value):
    try:
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def normalize(raw, current=None):
    """Reject incompatible/expired records; never infer skills or convert foreign pay."""
    current = current or datetime.now(timezone.utc)
    countries = raw.get("locationRestrictions")
    offsets = raw.get("timezoneRestrictions")
    if not isinstance(countries, list) or not isinstance(offsets, list):
        return None  # Missing eligibility facts must not be treated as worldwide.
    if countries and not {str(c).lower() for c in countries} & {"india", "in", "ind"}:
        return None
    try:
        if 5.5 not in [float(v) for v in offsets]:
            return None
    except (ValueError, TypeError):
        return None
    expires = timestamp(raw.get("expiryDate"))
    if not expires or datetime.fromisoformat(expires) <= current:
        return None
    guid, link = str(raw.get("guid") or ""), str(raw.get("applicationLink") or "")
    if urlparse(guid).hostname != "himalayas.app" or not urlparse(guid).path.startswith("/companies/"):
        return None
    if urlparse(link).scheme not in ("https", "http") or not urlparse(link).hostname:
        return None
    if not raw.get("title") or not raw.get("companyName"):
        return None
    pay = "Salary not disclosed."
    if raw.get("minSalary") is not None or raw.get("maxSalary") is not None:
        pay = f"Advertised pay: {raw.get('currency') or 'currency unspecified'} {raw.get('minSalary')}–{raw.get('maxSalary')} {raw.get('salaryPeriod') or 'annual'}. Total CTC is not verified."
    # The app's salary_lpa field means verified INR total CTC. Feed pay is not necessarily CTC.
    job = {
        "title": raw["title"], "company": raw["companyName"],
        "location": "India (remote)" if countries else "Worldwide (India eligible)",
        "work_arrangement": "remote", "employment_type": raw.get("employmentType", ""),
        "salary_lpa": None, "required_skills": [], "preferred_skills": [],
        "description": pay + "\n\n" + plain(raw.get("description") or raw.get("excerpt")),
        "source_name": "Himalayas", "source_url": link,
        "posted_at": timestamp(raw.get("pubDate")),
    }
    return job, {"guid": guid, "expires_at": expires, "salary_text": pay}


def fetch_page(client, query, page):
    response = client.get(API + "/search", params={"q": query, "country": "IN", "sort": "recent", "page": page})
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("jobs"), list):
        raise ValueError("Unexpected job-source response")
    return body["jobs"]
