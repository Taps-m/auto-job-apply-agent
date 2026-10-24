from datetime import datetime, timedelta, timezone
import httpx
from app.core.db import tx, now
from app.modules.discovery import himalayas, service


def record(**changes):
    r = dict(title='Senior Credit Risk Manager',companyName='Example Bank',
             guid='https://himalayas.app/companies/example/jobs/risk',
             applicationLink='https://himalayas.app/companies/example/jobs/risk?utm_source=api',
             locationRestrictions=['India'],timezoneRestrictions=[5.5],
             expiryDate=(datetime.now(timezone.utc)+timedelta(days=2)).timestamp(),
             description='<p>Credit risk and Python.</p>',minSalary=100000,maxSalary=120000,currency='USD')
    return {**r, **changes}


def test_country_timezone_expiration_and_pay():
    assert himalayas.normalize(record(locationRestrictions=['United States'])) is None
    assert himalayas.normalize(record(timezoneRestrictions=[-5])) is None
    assert himalayas.normalize(record(timezoneRestrictions=None)) is None
    assert himalayas.normalize(record(expiryDate=1)) is None
    assert himalayas.normalize(record(applicationLink='javascript:alert(1)')) is None
    j, meta = himalayas.normalize(record())
    assert j['salary_lpa'] is None and 'USD' in j['description']
    assert '<p>' not in j['description'] and j['required_skills'] == []
    assert j['source_url'].endswith('?utm_source=api')


def test_import_dedup_and_scoring(profile, monkeypatch):
    monkeypatch.setattr(service,'queries',lambda: ({'pages_per_query':3,'request_interval_seconds':0},['credit risk']))
    calls=[]
    def handler(request):
        calls.append(request.url.params['page'])
        return httpx.Response(200,json={'jobs':[record()] if request.url.params['page']=='1' else []})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        for _ in range(2):
            with tx() as c:
                service.ensure(c)
                run_id=c.execute("INSERT INTO discovery_runs(started_at,status,detail,counts) VALUES(?,'running','','{}')",(now(),)).lastrowid
            service.run(run_id,client=client,wait=lambda _:False)
    with tx() as c:
        assert c.execute('SELECT count(*) FROM discovered_jobs').fetchone()[0]==1
        assert c.execute('SELECT count(*) FROM job_postings').fetchone()[0]==1
        assert c.execute('SELECT count(*) FROM job_matches').fetchone()[0]==1
    assert calls==['1','2','1','2']
    assert service.status()['last_run']['counts']['duplicates']==1


def test_rate_limit_and_expiry(client, monkeypatch):
    monkeypatch.setattr(service,'queries',lambda: ({'pages_per_query':1,'request_interval_seconds':0},['risk']))
    with tx() as c:
        service.ensure(c)
        run_id=c.execute("INSERT INTO discovery_runs(started_at,status,detail,counts) VALUES(?,'running','','{}')",(now(),)).lastrowid
    with httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(429))) as source:
        service.run(run_id,client=source,wait=lambda _:False)
    assert service.status()['last_run']['status']=='failed'
    assert 'rate limit' in service.status()['last_run']['detail']
    assert client.get('/api/discovery').status_code==200


def test_concurrent_run_rejected(client):
    service._lock.acquire()
    try:
        assert client.post('/api/discovery/run').status_code==409
    finally:
        service._lock.release()


def test_manual_schedule_not_due(client):
    assert client.put('/api/settings',json={'search_frequency':'manual'}).status_code==200
    assert service.due() is False


def test_expired_jobs_hidden_and_daily_schedule(client, profile):
    from app.modules.jobs import service as jobs
    payload, meta = himalayas.normalize(record())
    j = jobs.add_job(payload)['job']
    with tx() as c:
        service.ensure(c)
        c.execute('INSERT INTO discovered_jobs VALUES(?,?,?,?)',(meta['guid'],j['id'],'2000-01-01T00:00:00+00:00',meta['salary_text']))
    assert jobs.search()['jobs'] == []
    assert jobs.get_job(j['id'])['status'] == 'expired'
    client.put('/api/settings',json={'search_frequency':'daily'})
    assert service.due() is True
    with tx() as c:
        c.execute("INSERT INTO discovery_runs(started_at,status,detail,counts) VALUES(?,'completed','','{}')",(now(),))
    assert service.due() is False


def test_unexpected_source_shape_is_recorded(monkeypatch):
    monkeypatch.setattr(service,'queries',lambda: ({'pages_per_query':1,'request_interval_seconds':0},['risk']))
    with tx() as c:
        service.ensure(c)
        run_id=c.execute("INSERT INTO discovery_runs(started_at,status,detail,counts) VALUES(?,'running','','{}')",(now(),)).lastrowid
    with httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'unexpected':[]}))) as source:
        service.run(run_id,client=source,wait=lambda _:False)
    assert service.status()['last_run']['status']=='failed'
