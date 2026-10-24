import io
from PIL import Image


def test_links_do_not_erase_career_facts(client, profile):
    before = client.get('/api/profile').json()
    response = client.put('/api/profile/links', json={'website_url': 'https://example.com', 'github_url': 'https://github.com/Taps-m', 'linkedin_url': 'https://linkedin.com/in/example'})
    assert response.status_code == 200
    after = client.get('/api/profile').json()
    for key in ('headline', 'skills', 'notice_months', 'years_experience'):
        assert before['profile'][key] == after['profile'][key]
    assert before['preferences'] == after['preferences']
    assert client.get('/api/profile/assets').json()['links']['linkedin_url'].startswith('https://')
    assert client.put('/api/profile/links', json={'website_url': 'javascript:alert(1)'}).status_code == 400


def test_photo_upload_validation_removal_and_privacy(client):
    output = io.BytesIO()
    Image.new('RGB', (20, 20), 'blue').save(output, 'PNG')
    assert client.post('/api/profile/photo', files={'file': ('photo.png', output.getvalue(), 'image/png')}).status_code == 200
    assert client.get('/api/profile/photo').headers['content-type'] == 'image/png'
    assert client.post('/api/profile/photo', files={'file': ('fake.png', b'not an image', 'image/png')}).status_code == 400
    assert client.delete('/api/profile/photo').status_code == 200
    assert client.get('/api/profile/photo').status_code == 404
    client.post('/api/profile/photo', files={'file': ('photo.png', output.getvalue(), 'image/png')})
    assert client.post('/api/privacy/delete-all', json={'confirm': 'DELETE'}).status_code == 200
    assert client.get('/api/profile/assets').json()['has_photo'] is False
