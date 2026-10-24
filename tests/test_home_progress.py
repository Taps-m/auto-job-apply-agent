from app.core.db import USER_ID, now, tx
from app.modules.applications.analytics import snapshot
from conftest import job_payload


def record(client, n, score, status='submitted', submitted=True, saved=True):
    job = client.post('/api/jobs', json=job_payload(source_url=f'https://example.com/analytics/{n}',company=f'Analytics {n}')).json()['job']
    with tx() as c:
        t = now()
        cur = c.execute('INSERT INTO applications(user_id,job_id,status,submitted_at,created_at,updated_at) VALUES (?,?,?,?,?,?)',
                        (USER_ID,job['id'],status,t if submitted else None,t,t))
        if saved:
            snapshot(c,cur.lastrowid,score)
        else:
            c.execute('UPDATE job_matches SET score=? WHERE job_id=? AND user_id=?',(score,job['id'],USER_ID))
        return job['id'],cur.lastrowid


def test_progress_excludes_drafts_keeps_snapshot_and_tracks_past_interviews(client):
    record(client,1,80)
    job,app = record(client,2,80,'withdrawn')
    record(client,3,90,'approved',submitted=False)
    with tx() as c:
        c.execute('UPDATE job_matches SET score=99 WHERE job_id=?',(job,))
        c.execute('INSERT INTO application_events(application_id,at,kind,detail) VALUES (?,?,?,?)',(app,now(),'interview',''))
    r=client.get('/api/applications/progress').json()
    assert r['submitted']==2 and r['points'][80]['applications']==2
    assert r['points'][99]['applications']==0 and r['interview_rate']==50
    assert r['response_rate']==50


def test_empty_unknown_and_legacy_scores_are_explicit(client):
    assert client.get('/api/applications/progress').json()['interview_rate'] is None
    record(client,1,None)
    record(client,2,85,saved=False)
    r=client.get('/api/applications/progress').json()
    assert r['submitted']==2 and r['unscored']==1 and r['legacy_current_scores']==1
    assert r['points'][85]['applications']==1
