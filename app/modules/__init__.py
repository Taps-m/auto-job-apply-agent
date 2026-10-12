"""Module registry. Enabled modules are listed in config/app.json; each exposes `router` in router.py."""
from importlib import import_module

from fastapi import APIRouter


def load_routers(names: list[str]) -> list[APIRouter]:
    return [import_module(f"{__name__}.{name}.router").router for name in names]
