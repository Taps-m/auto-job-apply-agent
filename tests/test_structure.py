import ast
from pathlib import Path

from app import config
from app.main import app
from app.modules import load_routers

APP = Path(__file__).resolve().parent.parent / "app"


def test_every_configured_module_is_registered():
    names = config.app_config()["modules"]
    for name in names:
        assert (APP / "modules" / name / "router.py").exists()
    included = [r.original_router for r in app.routes if hasattr(r, "original_router")]
    assert included == load_routers(names)  # Same router objects, in configured order.
    assert all(router.routes for router in included)


def test_main_defines_no_routes_or_settings():
    tree = ast.parse((APP / "main.py").read_text(encoding="utf-8"))
    decorators = [d for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) for d in n.decorator_list]
    assert not decorators
    literals = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))]
    assert not literals
