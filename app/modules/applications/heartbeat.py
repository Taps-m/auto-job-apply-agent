"""Worker state survives dashboard/server restarts; no credentials in status."""
import json
import os
import time
from ...core.db import data_dir


def write(state='running'):
    path=data_dir()/'worker-status.json'
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'pid':os.getpid(),'state':state,'at':time.time()}),encoding='utf-8')
    temporary.replace(path)


def running():
    try:
        record=json.loads((data_dir()/'worker-status.json').read_text(encoding='utf-8'))
        return record['state']=='running' and 0 <= time.time()-record['at'] < 120
    except (OSError,ValueError,KeyError,TypeError):
        return False
