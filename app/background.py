"""Start local services without an open terminal or chat. Windows desktop only."""
import argparse
import json
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from . import config
from .core.db import data_dir, init
from .modules.applications import runner


@contextmanager
def single_instance():
    import msvcrt
    with (data_dir()/'background.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        yield


def listening():
    cfg=config.app_config()
    try:
        with socket.create_connection((cfg['host'],cfg['port']),timeout=1):
            return True
    except OSError:
        return False


def supervise():
    cfg=config.app_config()
    stop=data_dir()/'background-stop'
    stop.unlink(missing_ok=True)
    server=None
    failures=0
    worker_started=False
    try:
        while not stop.exists():
            if not listening():
                if server is not None and server.poll() is None:
                    time.sleep(2); continue
                if failures >= 3:
                    raise RuntimeError('Local server failed repeatedly; see background-server.log')
                with (data_dir()/'background-server.log').open('ab') as log:
                    server=subprocess.Popen([sys.executable,'-m','app.main'],cwd=config.ROOT,
                        stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                failures+=1
                time.sleep(3)
            # Start once. Explicit Stop worker remains respected; no forced restart.
            if not worker_started:
                runner.start()
                worker_started=True
            (data_dir()/'background-status.json').write_text(json.dumps({
                'state':'running','at':time.time(),'worker':runner.status()}),encoding='utf-8')
            time.sleep(3)
    finally:
        runner.stop()
        if server is not None and server.poll() is None:
            server.terminate()  # Only our own child; never kill an existing user server.
        (data_dir()/'background-status.json').write_text(json.dumps({'state':'stopped','at':time.time()}),encoding='utf-8')


def main():
    config.load_env(); init()
    parser=argparse.ArgumentParser()
    parser.add_argument('--stop',action='store_true')
    args=parser.parse_args()
    if args.stop:
        (data_dir()/'background-stop').touch(); runner.stop(); return
    try:
        with single_instance():
            supervise()
    except Exception as error:
        (data_dir()/'background-error.txt').write_text(str(error),encoding='utf-8')


if __name__=='__main__':
    main()
