"""Visible employer-form worker. Uses a dedicated local browser profile.

Run with python -m app.modules.applications.worker. Unsupported forms and
agreements stay open for the user; uncertain submissions are never retried.
"""
import re
import time
from urllib.parse import urlsplit
from contextlib import contextmanager

from ... import config
from ...core.db import data_dir, init
from ..documents import service as documents
from . import queue, service

CONFIRMATION = re.compile(r'(application (?:has been |was )?(?:successfully )?(?:submitted|received)|thank you for applying)', re.I)


@contextmanager
def exclusive_worker():
    """OS releases the lock on crashes; a second worker cannot recover live work."""
    lock = (data_dir() / 'worker.lock').open('a+b')
    try:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        if __import__('os').name == 'nt':
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        lock.close()


def fill_dover(page, application):
    """Only exact saved answers; no model-generated screening answers."""
    doc = documents.get(application['resume_document_id'])
    path = documents.path_of(doc)
    if not path.is_file():
        return ['Resume file is missing']
    autofill = page.get_by_role('button', name='Upload file', exact=True)
    if autofill.count() == 1:
        with page.expect_file_chooser() as choice:
            autofill.click()
        choice.value.set_files(str(path))
        # Wait for the employer's parser, bounded; never guess that it finished.
        from playwright.sync_api import expect
        expected_name = application['answers'].get('First Name')
        if not expected_name:
            return ['Add the verified First Name answer before continuing after autofill.']
        try:
            expect(page.get_by_role('textbox', name=re.compile(r'^First Name'))).to_have_value(expected_name, timeout=45000)
        except Exception:
            return ['Resume autofill did not finish with the verified name. Review the browser.']
    upload = page.get_by_role('button', name='Drag and drop file or browse computer (PDF, 5 MB maximum)', exact=True)
    if upload.count() != 1:
        return ['Resume upload control needs review']
    with page.expect_file_chooser() as choice:
        upload.click()
    choice.value.set_files(str(path))
    answers = application['answers']
    fields = page.get_by_role('textbox')
    missing = []
    for i in range(fields.count()):
        field = fields.nth(i)
        if not field.is_visible():
            continue
        label = field.evaluate("e => (Array.from(e.labels || []).map(x=>x.innerText).join(' ') || e.getAttribute('aria-label') || '').trim()")
        required = (field.get_attribute('required') is not None or field.get_attribute('aria-required') == 'true' or '*' in label)
        if not required:
            continue
        key = re.sub(r'\s*\*\s*$', '', label).strip()
        answer = answers.get(label, answers.get(key))
        if answer:
            field.fill(str(answer))
        else:
            missing.append(key or 'Unlabelled required field')
    for label, answer in answers.items():
        group = page.get_by_role('group', name=label, exact=True)
        if group.count() == 1 and (group.get_attribute('aria-required') == 'true' or '*' in label):
            radio = group.get_by_role('radio', name=str(answer), exact=True)
            if radio.count() == 1:
                radio.check()
    for group in page.get_by_role('group').all():
        if not group.is_visible():
            continue
        label = group.get_attribute('aria-label') or ''
        if (group.get_attribute('aria-required') == 'true' or '*' in label) and label not in answers:
            missing.append(label or 'Required selection needs a verified answer')
    return missing


def run_one(page, item):
    app_id = item['application_id']
    a = service.get(app_id)
    queue.eligibility(a)  # Recheck current score, preferences, expiry and resume.
    url = item['employer_url']
    if not queue.supported_url(url):
        raise ValueError('Unsupported employer URL')
    page.goto(url, wait_until='domcontentloaded')
    if not queue.supported_url(page.url):
        raise ValueError('Employer redirected to another destination; review required')
    page.get_by_role('textbox').first.wait_for(timeout=30000)
    body = page.locator('body').inner_text()
    if CONFIRMATION.search(body):
        queue.finish(app_id, 'uncertain', 'A confirmation was already visible before this attempt. Review before retrying.')
        return
    if re.search(r'verify you are human|sign in to apply|log in to apply', body, re.I):
        queue.finish(app_id, 'needs_attention', 'Complete sign-in or verification in the browser.')
        return
    missing = fill_dover(page, a)
    if missing:
        queue.finish(app_id, 'needs_attention', 'Required answers: ' + '; '.join(missing))
        return
    # Native validation includes required checkboxes, radio groups and selects.
    invalid = page.locator('input:invalid,textarea:invalid,select:invalid').count()
    if invalid:
        queue.finish(app_id, 'needs_attention', 'Complete the highlighted required fields in the browser.')
        return
    if re.search(r'by applying.{0,100}(agree|terms)|terms of service|terms and conditions', page.locator('body').inner_text(), re.I):
        queue.finish(app_id, 'needs_attention', 'The employer requires agreement to terms. Review them and submit in the open browser.')
        return
    service.open_employer_page(app_id)
    if (data_dir() / 'worker-stop').exists():
        queue.finish(app_id, 'needs_attention', 'Worker stopped before submission.')
        return
    try:
        page.get_by_role('button', name='Apply', exact=True).last.click()
        message = page.get_by_text(CONFIRMATION).first
        message.wait_for(timeout=30000)
        confirmation = message.inner_text()
        evidence = data_dir() / 'submission-evidence'
        evidence.mkdir(exist_ok=True)
        page.screenshot(path=str(evidence / f'{app_id}.png'), full_page=True)
        service.confirm_submitted(app_id, confirmation)
        queue.finish(app_id, 'submitted', confirmation)
    except Exception:
        queue.finish(app_id, 'uncertain', 'Apply was clicked, but confirmation was not verified. Check the employer before retrying.')


def main():
    config.load_env()
    init()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('Install worker dependencies: python -m pip install -r requirements-worker.txt')
        return
    # The profile retains login sessions locally; never reads browser passwords.
    with exclusive_worker(), sync_playwright() as p:
        context = p.chromium.launch_persistent_context(str(data_dir() / 'application-browser'), channel='msedge', headless=False)
        queue.recover()
        while not (data_dir() / 'worker-stop').exists():
            item = queue.claim()
            if not item:
                time.sleep(1)
                continue
            page = context.new_page()
            try:
                run_one(page, item)
            except Exception:
                queue.finish(item['application_id'], 'needs_attention', 'Form could not be completed. Review the open employer page; no automatic retry.')
            state = next(x['state'] for x in queue.listing() if x['application_id'] == item['application_id'])
            if state == 'submitted':
                page.close()
            else:
                # Keep one unresolved page visible, without opening hundreds of tabs.
                while not page.is_closed() and not (data_dir() / 'worker-stop').exists():
                    try:
                        message = page.get_by_text(CONFIRMATION).first
                        if (state == 'needs_attention' and queue.supported_url(page.url)
                                and urlsplit(page.url).path == urlsplit(item['employer_url']).path
                                and message.is_visible()):
                            current = service.get(item['application_id'])
                            if not current['submitted_at']:
                                if current['status'] == 'approved':
                                    service.open_employer_page(item['application_id'])
                                proof = data_dir() / 'submission-evidence'
                                proof.mkdir(exist_ok=True)
                                page.screenshot(path=str(proof / f"{item['application_id']}.jpg"), full_page=True)
                                service.confirm_submitted(item['application_id'], message.inner_text())
                            queue.finish(item['application_id'], 'submitted', 'Employer confirmation observed after browser review.')
                            page.close()
                            break
                    except Exception:
                        pass  # A navigation may temporarily make the page unavailable.
                    time.sleep(1)
        context.close()


if __name__ == '__main__':
    main()
