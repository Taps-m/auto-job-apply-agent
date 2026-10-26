import json
import time
from app.core.db import data_dir
from app.modules.applications import heartbeat, runner
from app import background


def test_worker_status_survives_server_process_restart(monkeypatch):
    monkeypatch.setattr(runner,'_process',None)
    heartbeat.write()
    assert runner.status()['running']
    heartbeat.write('stopped')
    assert not runner.status()['running']


def test_stale_and_corrupt_heartbeat_not_running():
    p=data_dir()/'worker-status.json'
    p.write_text(json.dumps({'state':'running','at':time.time()-130}),encoding='utf-8')
    assert not heartbeat.running()
    p.write_text('{bad',encoding='utf-8')
    assert not heartbeat.running()


def test_background_reuses_existing_server_and_stops_owned_worker(monkeypatch):
    monkeypatch.setattr(background,'listening',lambda:True)
    calls=[]
    monkeypatch.setattr(runner,'start',lambda:calls.append('start'))
    monkeypatch.setattr(runner,'stop',lambda:calls.append('stop'))
    monkeypatch.setattr(runner,'status',lambda:{'running':True})
    monkeypatch.setattr(background.subprocess,'Popen',lambda *a,**k: (_ for _ in ()).throw(AssertionError('Must not start a second server')))
    monkeypatch.setattr(background.time,'sleep',lambda _: (data_dir()/'background-stop').touch())
    monkeypatch.delattr(background.supervise,'worker_started',raising=False)
    background.supervise()
    assert calls==['start','stop']
