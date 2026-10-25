"""M06 Resume & document engine: upload, master resume, retrieval."""
import uuid
from pathlib import Path

from ... import config
from ...core.db import USER_ID, data_dir, now, row, rows, tx
from ...core.errors import ServiceError


def max_upload_bytes() -> int:
    return config.app_config()["max_upload_mb"] * 1024 * 1024


def folder() -> Path:
    return data_dir() / "documents"


def save(filename: str, content: bytes, is_master: bool, user_id=USER_ID, *, kind: str = "resume") -> dict:
    if kind not in ("resume", "cover_letter"):
        raise ServiceError("Choose resume or cover_letter")
    if kind == "cover_letter":
        is_master = False
    types = config.app_config()["allowed_document_types"]
    ext = Path(filename).suffix.lower()
    if ext not in types:
        raise ServiceError(f"Upload a {' or '.join(t.lstrip('.').upper() for t in types)} file")
    if len(content) > max_upload_bytes():
        raise ServiceError(f"File is larger than {config.app_config()['max_upload_mb']} MB")
    if not content.startswith(types[ext].encode()):
        raise ServiceError("The file content does not match its extension")
    folder().mkdir(parents=True, exist_ok=True)
    stored = folder() / f"{uuid.uuid4().hex}{ext}"
    stored.write_bytes(content)
    with tx() as c:
        if is_master:
            c.execute("UPDATE documents SET is_master=0 WHERE user_id=? AND kind='resume'", (user_id,))
        cur = c.execute("INSERT INTO documents(user_id, kind, filename, stored_path, is_master, uploaded_at)"
                        " VALUES (?,?,?,?,?,?)", (user_id, kind, Path(filename).name[:200], stored.name,
                                                  int(is_master), now()))
    return get(cur.lastrowid, user_id)


def get(doc_id: int, user_id=USER_ID) -> dict:
    with tx() as c:
        d = row(c.execute("SELECT * FROM documents WHERE id=? AND user_id=?", (doc_id, user_id)).fetchone())
    if not d:
        raise ServiceError("Document not found", 404)
    return d


def path_of(doc: dict) -> Path:
    return folder() / Path(doc["stored_path"]).name


def list_all(user_id=USER_ID) -> list:
    with tx() as c:
        return rows(c.execute("SELECT * FROM documents WHERE user_id=? ORDER BY uploaded_at DESC", (user_id,)))


def master_resume_id(user_id=USER_ID):
    with tx() as c:
        r = c.execute("SELECT id FROM documents WHERE user_id=? AND kind='resume' AND is_master=1"
                      " ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    return r["id"] if r else None


def set_master(doc_id: int, user_id=USER_ID) -> list:
    if get(doc_id, user_id)["kind"] != "resume":
        raise ServiceError("A cover letter cannot be the master resume")
    get(doc_id, user_id)
    with tx() as c:
        c.execute("UPDATE documents SET is_master=0 WHERE user_id=? AND kind='resume'", (user_id,))
        c.execute("UPDATE documents SET is_master=1 WHERE id=? AND user_id=?", (doc_id, user_id))
    return list_all(user_id)


def delete_files(user_id=USER_ID) -> None:
    for d in list_all(user_id):
        path_of(d).unlink(missing_ok=True)
