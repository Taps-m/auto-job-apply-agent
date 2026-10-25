from unittest.mock import Mock, MagicMock

from app.modules.applications.forms import answer_for
from app.modules.applications import worker


def test_exact_answers_ignore_case_and_required_marker():
    assert answer_for({'label':'First Name *','name':'firstName'}, {'First Name':'Tapomoy'}) == 'Tapomoy'
    assert answer_for({'label':'US work authorization *','name':'us'}, {'Indian citizenship':'Yes'}) is None


def test_cv_first_single_upload_required_only_and_radio(monkeypatch, tmp_path):
    resume=tmp_path/'resume.pdf'; resume.write_bytes(b'%PDF-test')
    monkeypatch.setattr(worker.documents,'get',lambda _: {})
    monkeypatch.setattr(worker.documents,'path_of',lambda _: resume)
    page=Mock()
    page.expect_file_chooser.return_value=MagicMock()
    upload=Mock(); upload.count.return_value=1
    required=Mock(); required.is_visible.return_value=True
    required.evaluate.return_value={'label':'First Name *','name':'firstName','required':True}
    required.input_value.return_value='Tapomoy'
    optional=Mock(); optional.is_visible.return_value=True
    optional.evaluate.return_value={'label':'Salary','name':'salary','required':False}
    group=Mock(); group.is_visible.return_value=True
    group.evaluate.return_value={'label':'Exclusive employment *','name':'','required':True}
    group.get_by_role.return_value.count.return_value=1
    fields=Mock(); fields.all.return_value=[required,optional]
    groups=Mock(); groups.all.return_value=[group]
    page.get_by_role.side_effect=lambda role, **kw: fields if role=='textbox' else groups if role=='radiogroup' else upload
    page.locator.return_value.count.return_value=0
    calls=[]
    upload.click.side_effect=lambda: calls.append('upload')
    required.fill.side_effect=lambda value: calls.append('fill')
    result=worker.fill_dover(page,{'resume_document_id':1,'answers':{'First Name':'Tapomoy','Exclusive employment':'Yes','Salary':'25'}})
    assert result==[]
    assert calls==['upload','fill']
    page.expect_file_chooser.assert_called_once()
    optional.fill.assert_not_called()
    group.get_by_role.return_value.check.assert_called_once()


def test_missing_resume_never_interacts_with_form(monkeypatch,tmp_path):
    monkeypatch.setattr(worker.documents,'get',lambda _: {})
    monkeypatch.setattr(worker.documents,'path_of',lambda _: tmp_path/'missing.pdf')
    page=Mock()
    assert worker.fill_dover(page,{'resume_document_id':1})==['Resume file is missing']
    page.get_by_role.assert_not_called()
