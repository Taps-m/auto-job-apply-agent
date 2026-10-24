"""Local profile photo and professional links, independent of career facts."""
import io
import json
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError

from ...core.db import USER_ID, tx
from ...core.errors import ServiceError

MAX_PHOTO_BYTES = 5 * 1024 * 1024
LINK_FIELDS = ('website_url', 'github_url', 'linkedin_url', 'other_url')


def _ensure(c):
    c.execute("CREATE TABLE IF NOT EXISTS profile_assets (user_id INTEGER PRIMARY KEY REFERENCES users(id),"
              " links TEXT NOT NULL DEFAULT '{}', photo BLOB)")


def get(user_id=USER_ID):
    with tx() as c:
        _ensure(c)
        p = c.execute('SELECT website_url, github_url FROM career_profiles WHERE user_id=?', (user_id,)).fetchone()
        a = c.execute('SELECT links, photo IS NOT NULL AS has_photo FROM profile_assets WHERE user_id=?', (user_id,)).fetchone()
    links = {key: '' for key in LINK_FIELDS}
    if p:
        links.update(dict(p))
    if a:
        saved = json.loads(a['links'])
        links.update({key: saved.get(key, '') for key in ('linkedin_url', 'other_url')})
    return {'links': links, 'has_photo': bool(a and a['has_photo'])}


def update_links(data, user_id=USER_ID):
    links = {}
    for key in LINK_FIELDS:
        value = str(data.get(key, '')).strip()
        parsed = urlparse(value)
        if value and (len(value) > 500 or parsed.scheme not in ('https', 'http') or not parsed.netloc):
            raise ServiceError('Professional links must be full http(s) URLs')
        links[key] = value
    with tx() as c:
        _ensure(c)
        c.execute("INSERT INTO profile_assets(user_id,links) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET links=excluded.links",
                  (user_id, json.dumps(links)))
        c.execute('UPDATE career_profiles SET website_url=?,github_url=? WHERE user_id=?',
                  (links['website_url'], links['github_url'], user_id))
    return get(user_id)


def save_photo(content, user_id=USER_ID):
    if not content or len(content) > MAX_PHOTO_BYTES:
        raise ServiceError('Choose a photo up to 5 MB')
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width * image.height > 20_000_000:
                raise ServiceError('Choose a JPG, PNG or WebP photo up to 20 megapixels')
            image.load()
            image = image.convert('RGB')
            image.thumbnail((512, 512))
            output = io.BytesIO()
            image.save(output, 'PNG')  # Re-encode pixels; discard embedded metadata.
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ServiceError('This file is not a supported photo')
    with tx() as c:
        _ensure(c)
        c.execute('INSERT INTO profile_assets(user_id,photo) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET photo=excluded.photo',
                  (user_id, output.getvalue()))
    return get(user_id)


def photo(user_id=USER_ID):
    with tx() as c:
        _ensure(c)
        saved = c.execute('SELECT photo FROM profile_assets WHERE user_id=?', (user_id,)).fetchone()
    if not saved or not saved['photo']:
        raise ServiceError('No photo uploaded', 404)
    return saved['photo']


def remove_photo(user_id=USER_ID):
    with tx() as c:
        _ensure(c)
        c.execute('UPDATE profile_assets SET photo=NULL WHERE user_id=?', (user_id,))
    return get(user_id)
