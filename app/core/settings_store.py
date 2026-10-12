"""Non-secret key/value settings (integration_settings table). Secrets stay in .env."""
import json

from .db import tx


def get(key: str, default=None):
    with tx() as c:
        r = c.execute("SELECT value FROM integration_settings WHERE key=?", (key,)).fetchone()
    return json.loads(r["value"]) if r else default


def put(key: str, value) -> None:
    with tx() as c:
        c.execute("INSERT INTO integration_settings(key, value) VALUES (?,?)"
                  " ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))
