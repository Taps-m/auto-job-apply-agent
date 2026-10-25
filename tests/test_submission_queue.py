import pytest

from app.core.errors import ServiceError
from app.modules.applications import queue
from app.core.db import tx, now
from app.modules.applications import service, worker
from unittest.mock import Mock


def candidate(score=80):
    return {'job': {'match': {'score': score, 'eligible': True, 'blockers': []}},
            'readiness': {'ready': True}, 'submitted_at': None, 'status': 'draft'}


def test_exact_threshold_and_rejections():
    queue.eligibility(candidate())
    for score in (79.9, None, float('nan'), float('inf'), 101):
        with pytest.raises(ServiceError):
            queue.eligibility(candidate(score))
    a = candidate()
    a['submitted_at'] = '2026-10-25'
    with pytest.raises(ServiceError):
        queue.eligibility(a)
    a = candidate()
    a['job']['match']['blockers'] = ['Salary below minimum']
    with pytest.raises(ServiceError):
        queue.eligibility(a)


def test_only_supported_https_employer_routes():
    assert queue.supported_url('https://app.dover.com/apply/company/job-id')
    for url in ('http://app.dover.com/apply/company/job-id',
                'https://app.dover.com.evil.test/apply/company/job-id',
                'https://user@app.dover.com/apply/company/job-id',
                'https://app.dover.com:1234/apply/company/job-id',
                'https://linkedin.com/jobs/1'):
        assert not queue.supported_url(url)


def seed(monkeypatch):
    with tx() as c:
        c.execute("INSERT INTO job_postings(id,title,company,source_name,source_url,dedupe_key,retrieved_at) VALUES (1,'Risk Manager','Test','Test','https://app.dover.com/apply/test/1','test',?)", (now(),))
        c.execute("INSERT INTO applications(id,user_id,job_id,status,created_at,updated_at) VALUES (1,1,1,'draft',?,?)", (now(), now()))
    a = candidate()
    a.update(id=1, job_id=1)
    monkeypatch.setattr(service, 'get', lambda *args: a)
    return a


def test_queue_duplicate_claim_and_crash_recovery(monkeypatch):
    seed(monkeypatch)
    queue.enqueue(1,'https://app.dover.com/apply/test/1')
    with pytest.raises(ServiceError):
        queue.enqueue(1,'https://app.dover.com/apply/test/1')
    assert queue.claim()['application_id'] == 1
    assert queue.claim() is None
    queue.recover()
    assert queue.listing()[0]['state'] == 'uncertain'
    assert queue.claim() is None


def test_cancel_prevents_claim(monkeypatch):
    seed(monkeypatch)
    queue.enqueue(1,'https://app.dover.com/apply/test/1')
    queue.cancel(1)
    assert queue.claim() is None


def test_click_timeout_is_uncertain_not_retryable(monkeypatch):
    seed(monkeypatch)
    page = Mock()
    page.url='https://app.dover.com/apply/test/1'
    page.locator.return_value.inner_text.return_value='Job application'
    page.locator.return_value.count.return_value=0
    page.get_by_role.return_value.last.click.side_effect=TimeoutError()
    monkeypatch.setattr(worker, 'fill_dover', lambda *args: [])
    monkeypatch.setattr(service, 'open_employer_page', Mock())
    finish=Mock(); monkeypatch.setattr(queue, 'finish', finish)
    confirm=Mock(); monkeypatch.setattr(service, 'confirm_submitted', confirm)
    worker.run_one(page, {'application_id':1,'employer_url':page.url})
    assert finish.call_args.args[1] == 'uncertain'
    confirm.assert_not_called()


def test_agreement_blocks_auto_submit(monkeypatch):
    seed(monkeypatch)
    page = Mock(); page.url='https://app.dover.com/apply/test/1'
    page.locator.return_value.inner_text.return_value="By applying you agree to terms"
    page.locator.return_value.count.return_value=0
    monkeypatch.setattr(worker, 'fill_dover', lambda *args: [])
    finish=Mock(); monkeypatch.setattr(queue, 'finish', finish)
    worker.run_one(page, {'application_id':1,'employer_url':page.url})
    assert finish.call_args.args[1]=='needs_attention'
    page.get_by_role.return_value.last.click.assert_not_called()


def test_confirmation_is_required_and_recorded(monkeypatch):
    seed(monkeypatch)
    page = Mock(); page.url='https://app.dover.com/apply/test/1'
    page.locator.return_value.inner_text.return_value='Job application'
    page.locator.return_value.count.return_value=0
    page.get_by_text.return_value.first.inner_text.return_value='Application submitted'
    monkeypatch.setattr(worker, 'fill_dover', lambda *args: [])
    monkeypatch.setattr(service, 'open_employer_page', Mock())
    confirm=Mock(); monkeypatch.setattr(service, 'confirm_submitted', confirm)
    finish=Mock(); monkeypatch.setattr(queue, 'finish', finish)
    worker.run_one(page, {'application_id':1,'employer_url':page.url})
    confirm.assert_called_once_with(1,'Application submitted')
    assert finish.call_args.args[1]=='submitted'
    page.screenshot.assert_called_once()


def test_unknown_required_answers_do_not_submit(monkeypatch):
    seed(monkeypatch)
    page=Mock(); page.url='https://app.dover.com/apply/test/1'
    page.locator.return_value.inner_text.return_value='Job application'
    monkeypatch.setattr(worker,'fill_dover',lambda *args:['Work authorization'])
    finish=Mock(); monkeypatch.setattr(queue,'finish',finish)
    worker.run_one(page,{'application_id':1,'employer_url':page.url})
    assert finish.call_args.args[1]=='needs_attention'
    page.get_by_role.return_value.last.click.assert_not_called()
