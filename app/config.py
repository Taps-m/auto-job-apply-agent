"""Loads all configuration from config/*.json and the environment. Nothing else hardcodes settings."""
import json
import os
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(os.environ.get("PJA_CONFIG_DIR", ROOT / "config"))


def load_env(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader so secrets live outside code and the database."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _read(name: str) -> dict:
    return json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))


@lru_cache
def app_config() -> dict:
    cfg = _read("app.json")
    cfg["port"] = int(os.environ.get("PORT", cfg["port"]))
    cfg["data_dir"] = Path(os.environ.get("PJA_DATA_DIR", ROOT / "data"))
    cfg["allowed_hosts"] = {f"{cfg['host']}:{cfg['port']}", f"localhost:{cfg['port']}", *cfg["extra_allowed_hosts"]}
    return cfg


@lru_cache
def default_preferences() -> dict:
    return _read("preferences.json")


@lru_cache
def matching_rules() -> dict:
    return _read("matching.json")


@lru_cache
def agent_config() -> dict:
    return _read("agent.json")


def gemini_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()
