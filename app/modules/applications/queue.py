"""Persistent, deduplicated employer-submission queue. Never infer submission."""
import math
from urllib.parse import urlsplit

from ...core.db import USER_ID, now, tx
from ...core.errors import ServiceError
from . import service


def ensure(c):
    c.execute('''CREATE TABLE IF NOT EXISTS submission_queue (
        application_id INTEGER PRIMARY KEY REFERENCES applications(id),
        user_id INTEGER NOT NULL, employer_url TEXT NOT NULL,
        state TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL)''')


def supported_url(url):
    if not isinstance(url, str):
        return False
    try:
        p = urlsplit(url)
        port = p.port
    except ValueError:
        return False
    return (p.scheme == 'https' and p.hostname == 'app.dover.com'
            and port in (None, 443) and not p.username and not p.password
            and p.path.startswith('/apply/') and len(p.path.strip('/').split('/')) == 3
            and all(p.path.strip('/').split('/')))


def eligibility(a):
    match = a['job'].get('match') or {}
    score = match.get('score')
    if not isinstance(score, (int, float)) or not math.isfinite(score) or not 80 <= score <= 100:
        raise ServiceError('A computed match of at least 80% is required', 422)
    if not match.get('eligible') or match.get('blockers'):
        raise ServiceError('This job does not meet your application preferences', 422)
    if not a['readiness']['ready']:
        raise ServiceError('Complete the missing application details first', 422)
    if a['submitted_at'] or a['status'] not in ('draft', 'approved'):
        raise ServiceError('This application cannot be queued again', 409)


def enqueue(app_id, employer_url, user_id=USER_ID):
    a = service.get(app_id, user_id)
    eligibility(a)
    if not supported_url(employer_url):
        raise ServiceError('This employer form is not supported yet. Use its application page.', 422)
    with tx() as c:
        ensure(c)
        c.execute('BEGIN IMMEDIATE')
        prior = c.execute('SELECT 1 FROM submission_queue WHERE application_id=?', (app_id,)).fetchone()
        duplicate = c.execute('''SELECT 1 FROM applications WHERE user_id=? AND job_id=?
            AND id<>? AND (submitted_at IS NOT NULL OR status IN ('approved','awaiting_confirmation'))''',
            (user_id, a['job_id'], app_id)).fetchone()
        if prior or duplicate:
            raise ServiceError('This job already has a queued or submitted application', 409)
        c.execute('INSERT INTO submission_queue VALUES (?,?,?,?,?,?)',
                  (app_id, user_id, employer_url, 'queued', '', now()))
        service._update(c, app_id, status='approved', approved_at=now())
        service._event(c, app_id, 'queued', 'Queued under your standing 80% application rule')
    return listing(user_id)


def listing(user_id=USER_ID):
    with tx() as c:
        ensure(c)
        return [dict(r) for r in c.execute('''SELECT q.*, j.company, j.title FROM submission_queue q
            JOIN applications a ON a.id=q.application_id JOIN job_postings j ON j.id=a.job_id
            WHERE q.user_id=? ORDER BY q.updated_at''', (user_id,))]


def claim(user_id=USER_ID):
    with tx() as c:
        ensure(c)
        c.execute('BEGIN IMMEDIATE')
        r = c.execute("SELECT * FROM submission_queue WHERE user_id=? AND state='queued' ORDER BY updated_at LIMIT 1",
                      (user_id,)).fetchone()
        if not r:
            return None
        c.execute("UPDATE submission_queue SET state='running',updated_at=? WHERE application_id=?", (now(), r['application_id']))
        return dict(r)


def finish(app_id, state, detail):
    if state not in ('needs_attention', 'submitted', 'uncertain'):
        raise ValueError('Invalid queue state')
    with tx() as c:
        ensure(c)
        c.execute('UPDATE submission_queue SET state=?,detail=?,updated_at=? WHERE application_id=?',
                  (state, detail[:2000], now(), app_id))
        service._event(c, app_id, 'submission_' + state, detail)


def recover():
    """A crashed click may have succeeded: never automatically retry it."""
    with tx() as c:
        ensure(c)
        c.execute("UPDATE submission_queue SET state='uncertain',detail=?,updated_at=? WHERE state='running'",
                  ('Worker stopped. Check the employer before attempting another submission.', now()))


def cancel(app_id, user_id=USER_ID):
    service.get(app_id, user_id)
    with tx() as c:
        ensure(c)
        changed = c.execute("UPDATE submission_queue SET state='cancelled',updated_at=? WHERE application_id=? AND user_id=? AND state='queued'",
                            (now(), app_id, user_id)).rowcount
        if not changed:
            raise ServiceError('Only waiting applications can be removed from the queue', 409)
        service._event(c, app_id, 'queue_cancelled', 'Removed from submission queue')
    return listing(user_id)
