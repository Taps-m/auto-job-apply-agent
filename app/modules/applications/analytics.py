"""Application dashboard: counts by match percentage and recorded outcomes."""
import math

from ...core.db import USER_ID, now, tx


def _ensure(c):
    c.execute('CREATE TABLE IF NOT EXISTS application_match_snapshots ('
              'application_id INTEGER PRIMARY KEY REFERENCES applications(id) ON DELETE CASCADE,'
              'score REAL, recorded_at TEXT NOT NULL)')


def snapshot(c, application_id, score):
    _ensure(c)
    value = float(score) if isinstance(score, (int, float)) and math.isfinite(score) and 0 <= score <= 100 else None
    c.execute('INSERT OR IGNORE INTO application_match_snapshots VALUES (?,?,?)',
              (application_id, value, now()))


def progress(user_id=USER_ID):
    with tx() as c:
        _ensure(c)
        records = c.execute('''SELECT a.id, a.status, s.application_id AS snapshot_id,
            s.score AS saved_score, m.score AS current_score,
            EXISTS(SELECT 1 FROM application_events e WHERE e.application_id=a.id
                AND e.kind IN ('interview','offer')) AS had_interview,
            EXISTS(SELECT 1 FROM application_events e WHERE e.application_id=a.id
                AND e.kind IN ('interview','offer','rejected')) AS had_response
            FROM applications a
            LEFT JOIN application_match_snapshots s ON s.application_id=a.id
            LEFT JOIN job_matches m ON m.job_id=a.job_id AND m.user_id=a.user_id
            WHERE a.user_id=? AND a.submitted_at IS NOT NULL''', (user_id,)).fetchall()
    points = [{'match_percent': n, 'applications': 0, 'interviews': 0} for n in range(101)]
    unknown = legacy = responses = interviews = 0
    for r in records:
        interview = bool(r['had_interview'] or r['status'] in ('interview', 'offer'))
        response = bool(r['had_response'] or r['status'] in ('interview', 'offer', 'rejected'))
        interviews += int(interview)
        responses += int(response)
        score = r['saved_score'] if r['snapshot_id'] is not None else r['current_score']
        if score is None or not math.isfinite(score) or not 0 <= score <= 100:
            unknown += 1
            continue
        if r['snapshot_id'] is None:
            legacy += 1
        bucket = int(math.floor(score + .5))
        points[bucket]['applications'] += 1
        points[bucket]['interviews'] += int(interview)
    total = len(records)
    return {'points': points, 'submitted': total, 'responses': responses, 'interviews': interviews,
            'response_rate': round(responses / total * 100, 1) if total else None,
            'interview_rate': round(interviews / total * 100, 1) if total else None,
            'unscored': unknown, 'legacy_current_scores': legacy, 'updated_at': now()}
