"""Local process controls. Browser starts only after the user selects Start."""
import importlib.util
import subprocess
import sys
import threading

from ... import config
from ...core.db import data_dir
from ...core.errors import ServiceError

_lock = threading.Lock()
_process = None


def status():
    return {'running': _process is not None and _process.poll() is None,
            'installed': importlib.util.find_spec('playwright') is not None,
            'supported': ['Dover employer forms'],
            'live_verified': False}


def start():
    global _process
    with _lock:
        if status()['running']:
            return status()
        if not status()['installed']:
            raise ServiceError('Install requirements-worker.txt in the project environment first.', 422)
        data_dir().mkdir(exist_ok=True, parents=True)
        (data_dir() / 'worker-stop').unlink(missing_ok=True)
        with (data_dir() / 'worker.log').open('ab') as log:
            _process = subprocess.Popen([sys.executable, '-m', 'app.modules.applications.worker'],
                cwd=config.ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return status()


def stop():
    data_dir().mkdir(exist_ok=True, parents=True)
    (data_dir() / 'worker-stop').touch()
    return {'stopping': status()['running']}
