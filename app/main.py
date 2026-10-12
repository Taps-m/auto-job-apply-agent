"""Entry point: loads configuration, prepares storage and registers the enabled modules."""
from fastapi import FastAPI

from . import config
from .core import db, security
from .modules import load_routers


def create_app() -> FastAPI:
    config.load_env()
    cfg = config.app_config()
    db.init()
    app = FastAPI(title=cfg["name"], version=cfg["version"], docs_url=None, redoc_url=None)
    security.install(app)
    for router in load_routers(cfg["modules"]):
        app.include_router(router)
    return app


app = create_app()


def run() -> None:
    import uvicorn
    cfg = config.app_config()
    print(f"{cfg['name']} {cfg['version']} — http://{cfg['host']}:{cfg['port']}")
    uvicorn.run(app, host=cfg["host"], port=cfg["port"], log_level="warning")


if __name__ == "__main__":
    run()
