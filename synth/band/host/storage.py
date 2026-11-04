"""Atomic JSON writes shared by presets/scenes; failure preserves the previous file."""
import json
import os
import tempfile
from pathlib import Path

def atomic_json(path,data):
    path=Path(path)
    content=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)
    fd,name=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            f.write(content);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
