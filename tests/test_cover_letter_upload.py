def test_cover_letter_keeps_master_resume(client):
    resume = client.post('/api/documents', files={'file':('resume.pdf',b'%PDF-1.4 resume','application/pdf')}).json()
    content = b'%PDF-1.4 letter'
    response = client.post('/api/documents', data={'kind':'cover_letter','is_master':'true'}, files={'file':('Cover Letter.pdf',content,'application/pdf')})
    assert response.status_code == 200
    letter = response.json()
    assert letter['kind'] == 'cover_letter' and not letter['is_master']
    assert next(d for d in client.get("/api/documents").json() if d["id"] == resume["id"])["is_master"]
    assert client.get(f"/api/documents/{letter['id']}/file").content == content
    assert client.post(f"/api/documents/{letter['id']}/master").status_code == 400
    assert next(d for d in client.get("/api/documents").json() if d["id"] == resume["id"])["is_master"]


def test_reject_unknown_kind_and_invalid_pdf(client):
    assert client.post('/api/documents', data={'kind':'other'}, files={'file':('letter.pdf',b'%PDF-1.4','application/pdf')}).status_code == 400
    assert client.post('/api/documents', data={'kind':'cover_letter'}, files={'file':('letter.pdf',b'not a pdf','application/pdf')}).status_code == 400
    assert client.get('/api/documents').json() == []
